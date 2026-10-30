import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from services import local_auth


class FakeCursor:
    def __init__(self, result=None):
        self.result = result
        self.statements = []

    def execute(self, query, parameters=()):
        self.statements.append((query, parameters))

    def fetchone(self):
        return self.result

    def close(self):
        pass


class FakeConnection:
    def __init__(self, result=None):
        self.test_cursor = FakeCursor(result)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def cursor(self, dictionary=False):
        assert dictionary
        return self.test_cursor


def test_signup_validates_and_normalizes_citizen_details():
    request = local_auth.SignupRequest(
        full_name="  Jordan   Citizen ",
        email=" JORDAN@example.com ",
        mobile="+1 (555) 123-4567",
        password="safe-password",
    )

    assert request.full_name == "Jordan Citizen"
    assert request.email == "jordan@example.com"
    assert request.mobile == "+1 (555) 123-4567"


def test_signup_rejects_invalid_email():
    with pytest.raises(ValidationError):
        local_auth.SignupRequest(
            full_name="Jordan Citizen",
            email="not-an-email",
            mobile="5551234567",
            password="safe-password",
        )


def test_register_creates_citizen_and_returns_login_session(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(local_auth, "get_connection", lambda: connection)
    monkeypatch.setattr(local_auth, "_signing_secret", lambda: b"test-secret" * 4)

    result = local_auth.register(
        local_auth.SignupRequest(
            full_name="Jordan Citizen",
            email="jordan@example.com",
            mobile="5551234567",
            password="safe-password",
        )
    )

    assert result["user"]["role"] == "citizen"
    assert result["user"]["name"] == "Jordan Citizen"
    assert result["user"]["id"].startswith("CW-CIT-")
    assert result["access_token"]
    insert_query, insert_values = connection.test_cursor.statements[1]
    assert "INSERT INTO users" in insert_query
    assert insert_values[2] == "jordan@example.com"
    assert local_auth.verify_password("safe-password", insert_values[4])


def test_register_rejects_duplicate_email(monkeypatch):
    connection = FakeConnection({"id": "CW-CIT-EXISTING"})
    monkeypatch.setattr(local_auth, "get_connection", lambda: connection)

    with pytest.raises(HTTPException) as error:
        local_auth.register(
            local_auth.SignupRequest(
                full_name="Jordan Citizen",
                email="jordan@example.com",
                mobile="5551234567",
                password="safe-password",
            )
        )

    assert error.value.status_code == 409


def test_login_query_supports_email_and_account_id(monkeypatch):
    password_hash = local_auth.hash_password("safe-password")
    connection = FakeConnection({
        "id": "CW-CIT-EXISTING",
        "full_name": "Jordan Citizen",
        "role": "citizen",
        "department_id": None,
        "password_hash": password_hash,
        "is_active": 1,
    })
    monkeypatch.setattr(local_auth, "get_connection", lambda: connection)
    monkeypatch.setattr(local_auth, "_signing_secret", lambda: b"test-secret" * 4)

    result = local_auth.login(
        local_auth.LoginRequest(id="jordan@example.com", password="safe-password")
    )

    assert result["user"]["id"] == "CW-CIT-EXISTING"
    query, parameters = connection.test_cursor.statements[0]
    assert "LOWER(email) = LOWER(%s)" in query
    assert parameters == ("jordan@example.com", "jordan@example.com")
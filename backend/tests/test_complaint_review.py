import pytest
from fastapi import HTTPException

from routes import assignments, complaints


class FakeCursor:
    def __init__(self, complaint_status="Pending Review"):
        self.statements = []
        self.result = None
        self.complaint_status = complaint_status

    def execute(self, query, parameters=()):
        self.statements.append((query, parameters))
        normalized_query = query.lstrip()
        if normalized_query.startswith("SELECT status FROM complaints"):
            self.result = {"status": self.complaint_status}
        elif normalized_query.startswith("SELECT id, name FROM departments"):
            self.result = {"id": "drainage", "name": "Drainage Department"}

    def fetchone(self):
        return self.result

    def fetchall(self):
        return []

    def close(self):
        pass


class FakeConnection:
    def __init__(self, complaint_status="Pending Review"):
        self.test_cursor = FakeCursor(complaint_status)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def start_transaction(self):
        pass

    def cursor(self, dictionary=False):
        assert dictionary
        return self.test_cursor


@pytest.mark.asyncio
async def test_officer_can_approve_and_route_pending_complaint(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(complaints, "get_connection", lambda: connection)

    result = await complaints.verify_complaint(
        "complaint-1",
        complaints.VerifyRequest(department_id="drainage"),
        {"id": "officer-1", "role": "officer"},
    )

    assert result == {
        "id": "complaint-1",
        "status": "Verified",
        "assigned_department_id": "drainage",
        "department": "Drainage Department",
    }
    update = next(
        (query, parameters)
        for query, parameters in connection.test_cursor.statements
        if query.lstrip().startswith("UPDATE complaints")
    )
    assert "assigned_department_id = %s" in update[0]
    assert update[1][0] == "drainage"


@pytest.mark.asyncio
async def test_officer_can_approve_submitted_complaint(monkeypatch):
    connection = FakeConnection(complaint_status="Submitted")
    monkeypatch.setattr(complaints, "get_connection", lambda: connection)

    result = await complaints.verify_complaint(
        "complaint-1",
        complaints.VerifyRequest(department_id="drainage"),
        {"id": "officer-1", "role": "officer"},
    )

    assert result["status"] == "Verified"


@pytest.mark.asyncio
async def test_already_verified_complaint_cannot_be_approved_again(monkeypatch):
    connection = FakeConnection(complaint_status="Verified")
    monkeypatch.setattr(complaints, "get_connection", lambda: connection)

    with pytest.raises(HTTPException) as error:
        await complaints.verify_complaint(
            "complaint-1",
            complaints.VerifyRequest(department_id="drainage"),
            {"id": "officer-1", "role": "officer"},
        )

    assert error.value.status_code == 409
    assert "submitted or pending-review" in error.value.detail
    assert not any(
        query.lstrip().startswith("UPDATE complaints")
        for query, _parameters in connection.test_cursor.statements
    )


@pytest.mark.asyncio
async def test_citizen_cannot_approve_complaint():
    with pytest.raises(HTTPException) as error:
        await complaints.verify_complaint(
            "complaint-1",
            complaints.VerifyRequest(department_id="drainage"),
            {"id": "citizen-1", "role": "citizen"},
        )

    assert error.value.status_code == 403


def test_officer_assignments_include_ai_routed_pending_department_queue(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(assignments, "get_connection", lambda: connection)

    result = assignments.get_assignments({
        "id": "officer-1",
        "role": "officer",
        "department_id": "roads-department",
    })

    assert result == []
    query, parameters = connection.test_cursor.statements[0]
    assert "UNION ALL" in query
    assert "LOWER(REPLACE(TRIM(c.status), '_', ' ')) = 'pending review'" in query
    assert "ORDER BY analysis.id DESC LIMIT 1" in query
    assert "LOWER(TRIM(ai.analysis_status)) = 'completed'" in query
    assert "NOT EXISTS" in query
    assert parameters == ("officer-1", "roads-department")


@pytest.mark.asyncio
async def test_officer_complaints_are_scoped_to_their_department(monkeypatch):
    connection = FakeConnection()
    monkeypatch.setattr(complaints, "get_connection", lambda: connection)

    await complaints.list_complaints({
        "id": "officer-1",
        "role": "officer",
        "department_id": "roads-department",
    })

    query, parameters = connection.test_cursor.statements[0]
    assert "c.assigned_department_id IS NULL" in query
    assert "LOWER(TRIM(c.status)) = 'verified'" in query
    assert parameters == ("roads-department", "officer-1", "roads-department")

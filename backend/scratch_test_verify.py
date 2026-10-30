import sys
print("STEP 0: starting", flush=True)
sys.path.insert(0, "CityWatchAI/backend")

print("STEP 1: importing routes.complaints", flush=True)
from routes import complaints

print("STEP 2: importing tests.test_complaint_review", flush=True)
from tests.test_complaint_review import FakeConnection

print("STEP 3: importing fastapi", flush=True)
from fastapi import HTTPException
import asyncio

async def run():
    print("STEP 4: inside async run", flush=True)
    conn = FakeConnection(complaint_status="Verified")
    complaints.get_connection = lambda: conn
    try:
        print("STEP 5: calling verify_complaint", flush=True)
        await complaints.verify_complaint(
            "c1",
            complaints.VerifyRequest(department_id="drainage"),
            {"id": "off1", "role": "officer"},
        )
        print("FAIL: Expected HTTPException was not raised", flush=True)
    except HTTPException as exc:
        if exc.status_code == 409:
            print("PASS: HTTPException 409 raised as expected", flush=True)
        else:
            print(f"FAIL: Wrong status code {exc.status_code}", flush=True)

print("STEP 6: calling asyncio.run", flush=True)
asyncio.run(run())
print("STEP 7: finished", flush=True)

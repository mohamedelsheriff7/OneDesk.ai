import json
import os
import threading
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
EMPLOYEE_FILE = BASE_DIR / "employee_directory.json"
REQUEST_FILE = BASE_DIR / "requests_db.json"
STORE_LOCK = threading.Lock()

app = FastAPI(
    title="Employee Requests API",
    version="1.0.0",
    description=(
        "Mock API for verifying employees, submitting employee requests, "
        "and checking request status. Submitting a request does not approve it."
    ),
)


class RequestSubmission(BaseModel):
    employee_id: str = Field(..., examples=["EMP101"])
    request_type: Literal["Leave", "HR Letter", "Hardware", "Software Access"]
    details: str = Field(..., min_length=3)
    confirmed: bool


def load_json(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def atomic_write_json(path: Path, records: list[dict]) -> None:
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as stream:
        json.dump(records, stream, indent=2, ensure_ascii=False)
        temp_name = stream.name
    os.replace(temp_name, path)


def find_employee(employee_id: str) -> dict | None:
    normalized = employee_id.strip().upper()
    return next(
        (employee for employee in load_json(EMPLOYEE_FILE)
         if employee["employee_id"].upper() == normalized),
        None,
    )


@app.get("/", include_in_schema=False)
def health() -> dict:
    return {
        "service": "Employee Requests API",
        "status": "running",
        "openapi": "/openapi.json",
        "docs": "/docs",
    }


@app.get(
    "/employees/{employee_id}",
    operation_id="resolve_employee",
    summary="Resolve employee identity",
    description=(
        "Verifies an employee ID and returns only the employee's basic name, "
        "department, and company email."
    ),
)
def resolve_employee(employee_id: str) -> dict:
    employee = find_employee(employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return {
        "success": True,
        "employee_id": employee["employee_id"],
        "name": employee["name"],
        "department": employee["department"],
        "email": employee["email"],
    }


@app.post(
    "/requests",
    status_code=201,
    operation_id="submit_request",
    summary="Submit an employee request",
    description=(
        "Creates a leave, HR letter, hardware, or software-access request for a "
        "verified employee after explicit confirmation. Submission does not mean approval."
    ),
)
def submit_request(payload: RequestSubmission) -> dict:
    employee = find_employee(payload.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found. No request was submitted.")
    if payload.confirmed is not True:
        raise HTTPException(status_code=400, detail="Explicit confirmation is required. No request was submitted.")

    with STORE_LOCK:
        records = load_json(REQUEST_FILE)
        numeric_ids = []
        for record in records:
            try:
                numeric_ids.append(int(record["request_id"].split("-")[-1]))
            except (KeyError, ValueError):
                continue
        next_number = max(numeric_ids, default=1000) + 1
        request_id = f"REQ-{next_number}"
        record = {
            "request_id": request_id,
            "employee_id": employee["employee_id"],
            "type": payload.request_type,
            "details": payload.details.strip(),
            "status": "Submitted",
            "submitted_at": date.today().isoformat(),
        }
        records.append(record)
        atomic_write_json(REQUEST_FILE, records)

    return {
        "success": True,
        **record,
        "message": "The request was submitted for review. Submission does not mean approval.",
    }


@app.get(
    "/requests/{request_id}",
    operation_id="check_request_status",
    summary="Check request status",
    description=(
        "Returns a request only when the supplied request ID belongs to the "
        "supplied verified employee ID."
    ),
)
def check_request_status(
    request_id: str,
    employee_id: str = Query(..., description="Verified employee ID, for example EMP101"),
) -> dict:
    if not find_employee(employee_id):
        raise HTTPException(status_code=404, detail="No matching request was found for this employee.")

    normalized_request = request_id.strip().upper()
    normalized_employee = employee_id.strip().upper()
    record = next(
        (
            item for item in load_json(REQUEST_FILE)
            if item.get("request_id", "").upper() == normalized_request
            and item.get("employee_id", "").upper() == normalized_employee
        ),
        None,
    )
    if not record:
        raise HTTPException(status_code=404, detail="No matching request was found for this employee.")
    return {"success": True, **record}

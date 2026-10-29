"""Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ── Complaints ──────────────────────────────────────────────

class ComplaintCreate(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    category: str
    description: str = Field(..., min_length=5, max_length=2000)
    location_text: Optional[str] = Field(None, max_length=300)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ward: Optional[str] = None
    priority: str = "medium"


class ComplaintUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    location_text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ward: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str
    reason: Optional[str] = None


# ── Review ──────────────────────────────────────────────────

class ReviewAction(BaseModel):
    action: str = Field(..., description="verify, reject, needs_information, override_priority")
    reason: Optional[str] = None
    new_priority: Optional[str] = None


# ── Assignment ──────────────────────────────────────────────

class AssignmentCreate(BaseModel):
    officer_id: str
    department_id: Optional[str] = None
    notes: Optional[str] = None


# ── Resolution ──────────────────────────────────────────────

class ResolutionCreate(BaseModel):
    resolution_notes: str = Field(..., min_length=5, max_length=2000)
    evidence_file_id: Optional[str] = None


# ── Reopen ──────────────────────────────────────────────────

class ReopenRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=1000)


# ── Department ──────────────────────────────────────────────

class DepartmentCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    jurisdiction: Optional[str] = None
    issue_categories: list[str] = []


# ── Auth ────────────────────────────────────────────────────

class SignUpRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = "citizen"

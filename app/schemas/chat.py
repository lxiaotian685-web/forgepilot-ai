from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.document import Evidence


class Statement(BaseModel):
    type: Literal["fact", "inference", "pending"]
    text: str
    source: str | None = None
    source_ids: list[str] = []


class ConflictSource(BaseModel):
    origin: str
    value: str
    ref: str | None = None


class Conflict(BaseModel):
    field: str
    sources: list[ConflictSource]


class VerificationSuggestion(BaseModel):
    missing_evidence: str
    to_verify: str


class ChatRequest(BaseModel):
    device_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    equipment_model: str | None = None


class ChatResponse(BaseModel):
    device_id: str
    answer: str
    statements: list[Statement]
    sources: list[Evidence]
    conflicts: list[Conflict] = []
    verification_suggestions: list[VerificationSuggestion] = []
    is_mock: bool
    status: str = "ok"

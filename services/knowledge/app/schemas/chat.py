from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.document import Evidence

DiagnosisStatus = Literal[
    "ok",
    "no_answer",
    "model_unavailable",
    "device_not_found",
    "device_unauthorized",
    "device_unavailable",
    "device_mismatch",
    "no_knowledge",
    "model_mismatch",
]

MAX_DEVICE_ID_LENGTH = 100
MAX_QUESTION_LENGTH = 2_000
MAX_ANSWER_LENGTH = 8_000


class Statement(BaseModel):
    type: Literal["fact", "inference", "pending"]
    text: str = Field(min_length=1, max_length=2_000)
    source: str | None = Field(default=None, max_length=500)
    source_ids: list[str] = Field(default_factory=list, max_length=20)


class ConflictSource(BaseModel):
    origin: str = Field(min_length=1, max_length=100)
    value: str = Field(min_length=1, max_length=500)
    ref: str | None = Field(default=None, max_length=200)


class Conflict(BaseModel):
    field: str = Field(min_length=1, max_length=200)
    sources: list[ConflictSource] = Field(default_factory=list, max_length=20)


class VerificationSuggestion(BaseModel):
    missing_evidence: str = Field(min_length=1, max_length=1_000)
    to_verify: str = Field(min_length=1, max_length=1_000)


class ChatRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=MAX_DEVICE_ID_LENGTH)
    question: str = Field(min_length=1, max_length=MAX_QUESTION_LENGTH)
    equipment_model: str | None = Field(default=None, max_length=100)

    @field_validator("device_id", "question")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("不能为空白字符")
        return value


class ChatResponse(BaseModel):
    device_id: str
    answer: str = Field(max_length=MAX_ANSWER_LENGTH)
    summary: str = Field(default="", max_length=MAX_ANSWER_LENGTH)
    statements: list[Statement]
    sources: list[Evidence]
    conflicts: list[Conflict] = Field(default_factory=list)
    verification_suggestions: list[VerificationSuggestion] = Field(
        default_factory=list
    )
    is_mock: bool
    device_source: str = "static"
    is_demo: bool = True
    status: DiagnosisStatus = "ok"

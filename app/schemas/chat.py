from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.document import Evidence


class Statement(BaseModel):
    type: Literal["fact", "inference", "pending"]
    text: str
    source: str | None = None


class ChatRequest(BaseModel):
    device_id: str = Field(min_length=1)
    question: str = Field(min_length=1)
    equipment_model: str | None = None


class ChatResponse(BaseModel):
    device_id: str
    answer: str
    statements: list[Statement]
    sources: list[Evidence]
    is_mock: bool
    status: str = "ok"

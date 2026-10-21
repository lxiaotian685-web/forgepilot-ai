from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.capitalize() for part in tail)


class RequestModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class AlertAcknowledgeRequest(RequestModel):
    note: str | None = Field(default=None, max_length=500)


class DiagnosisCreate(RequestModel):
    device_id: str = Field(min_length=1)
    question: str = Field(min_length=1, max_length=2000)
    conclusion: str = Field(min_length=1, max_length=5000)
    risk_level: str = Field(default="low")
    confidence: float | None = Field(default=None, ge=0, le=100)
    model_source: str | None = Field(default=None, max_length=120)
    evidence: dict | list | None = None
    alert_id: str | None = None


class DiagnosisConfirm(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    priority: str | None = None
    owner_id: UUID | None = None
    due_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class WorkOrderCreate(RequestModel):
    title: str = Field(min_length=1, max_length=255)
    device_id: str = Field(min_length=1)
    priority: str | None = None
    description: str | None = Field(default=None, max_length=2000)
    owner_id: UUID | None = None
    due_at: datetime | None = None
    alert_id: str | None = None
    diagnosis_id: str | None = None


class WorkOrderUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    priority: str | None = None
    status: str | None = None
    owner_id: UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    due_at: datetime | None = None

    @model_validator(mode="after")
    def _require_one_field(self) -> "WorkOrderUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个可更新字段")
        return self

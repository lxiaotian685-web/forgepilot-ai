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


class AlertCreate(RequestModel):
    device_id: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=255)
    level: str = Field(default="p2")
    description: str | None = Field(default=None, max_length=2000)
    owner_id: UUID | None = None


class AlertUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    level: str | None = None
    description: str | None = Field(default=None, max_length=2000)
    owner_id: UUID | None = None
    status: str | None = None

    @model_validator(mode="after")
    def _require_one_field(self) -> "AlertUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个可更新字段")
        return self


class LoginRequest(RequestModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=200)
    organization_code: str | None = Field(default=None, max_length=64)


class MemberCreate(RequestModel):
    email: str = Field(min_length=3, max_length=255)
    display_name: str = Field(min_length=1, max_length=100)
    role: str = Field(default="viewer")
    initial_password: str | None = Field(default=None, min_length=8, max_length=200)


class MemberUpdate(RequestModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    role: str | None = None
    status: str | None = None
    reassign_to_user_id: UUID | None = None

    @model_validator(mode="after")
    def _require_one_member_field(self) -> "MemberUpdate":
        if not ({"display_name", "role", "status"} & self.model_fields_set):
            raise ValueError("至少提供姓名、角色或状态中的一个字段")
        return self


class DeviceImportRow(RequestModel):
    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=200)
    type: str = Field(min_length=1, max_length=120)
    plant: str = Field(min_length=1, max_length=200)
    location: str = Field(min_length=1, max_length=255)


class DeviceImportRequest(RequestModel):
    items: list[DeviceImportRow] = Field(min_length=1, max_length=100)


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
    planned_start_at: datetime | None = None
    due_at: datetime | None = None
    note: str | None = Field(default=None, max_length=500)


class DeviceParameterCreate(RequestModel):
    name: str = Field(min_length=1, max_length=120)
    value: float
    unit: str | None = Field(default=None, max_length=32)
    source: str = Field(default="sensor")
    source_ref: str | None = Field(default=None, max_length=255)
    is_authoritative: bool | None = None
    recorded_at: datetime | None = None


class DeviceParameterUpdate(RequestModel):
    value: float | None = None
    unit: str | None = Field(default=None, max_length=32)
    source: str | None = None
    source_ref: str | None = Field(default=None, max_length=255)
    is_authoritative: bool | None = None
    recorded_at: datetime | None = None

    @model_validator(mode="after")
    def _require_one_field(self) -> "DeviceParameterUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个可更新字段")
        return self


class WorkOrderCreate(RequestModel):
    title: str = Field(min_length=1, max_length=255)
    device_id: str = Field(min_length=1)
    priority: str | None = None
    description: str | None = Field(default=None, max_length=2000)
    owner_id: UUID | None = None
    planned_start_at: datetime | None = None
    due_at: datetime | None = None
    alert_id: str | None = None
    diagnosis_id: str | None = None


class WorkOrderUpdate(RequestModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    priority: str | None = None
    status: str | None = None
    owner_id: UUID | None = None
    description: str | None = Field(default=None, max_length=2000)
    planned_start_at: datetime | None = None
    due_at: datetime | None = None
    cancel_reason: str | None = Field(default=None, min_length=1, max_length=500)

    @model_validator(mode="after")
    def _require_one_field(self) -> "WorkOrderUpdate":
        if not self.model_fields_set:
            raise ValueError("至少提供一个可更新字段")
        return self

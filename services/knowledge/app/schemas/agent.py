from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.chat import ChatRequest, ChatResponse


class AgentRequest(ChatRequest):
    pass


class ToolStep(BaseModel):
    name: Literal["device_lookup", "work_order_history", "evidence_diagnosis"]
    status: Literal["ok", "unavailable", "skipped"]
    summary: str
    count: int = 0


class HistoryOrder(BaseModel):
    id: str
    device_id: str
    title: str
    status: str


class AgentResponse(BaseModel):
    device_id: str
    status: Literal["ready_for_review", "needs_evidence", "unavailable"]
    diagnosis: ChatResponse | None = None
    history: list[HistoryOrder] = Field(default_factory=list)
    tools: list[ToolStep]
    requires_human_confirmation: bool = True
    can_create_work_order: bool = False
    is_demo: bool = True
    audit_status: Literal["recorded", "unavailable"] = "unavailable"
    audit_id: str | None = None

from __future__ import annotations

import hmac
import os
import uuid
from typing import Literal

from fastapi import APIRouter, Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.audit import write_audit
from app.api.deps import RequestContext, get_context, require_role
from app.api.errors import api_error
from app.db import get_db
from app.models import AuditLog, Device

router = APIRouter(prefix="/api/v1/agent-runs", tags=["agent-runs"])


class ToolRecord(BaseModel):
    name: Literal["device_lookup", "work_order_history", "evidence_diagnosis"]
    status: Literal["ok", "unavailable", "skipped"]
    count: int = Field(ge=0, le=100)


class AgentRunAudit(BaseModel):
    run_id: uuid.UUID = Field(alias="runId")
    device_id: str = Field(min_length=1, max_length=100, alias="deviceId")
    status: Literal["ready_for_review", "needs_evidence", "unavailable"]
    diagnosis_status: str | None = Field(default=None, max_length=50, alias="diagnosisStatus")
    is_demo: bool = Field(alias="isDemo")
    tools: list[ToolRecord] = Field(min_length=1, max_length=3)


@router.post("/audit", status_code=201)
def record_agent_run(
    payload: AgentRunAudit,
    authorization: str | None = Header(default=None, alias="Authorization"),
    agent_audit_key: str | None = Header(default=None, alias="X-Agent-Audit-Key"),
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise api_error(401, "UNAUTHORIZED", "Agent 审计需要当前用户令牌")
    secret = os.getenv("AGENT_AUDIT_KEY", "")
    if not secret:
        raise api_error(503, "UNAVAILABLE", "Agent 审计服务尚未配置")
    if not agent_audit_key or not hmac.compare_digest(secret, agent_audit_key):
        raise api_error(403, "FORBIDDEN", "Agent 审计服务凭证无效")
    require_role(context, "technician")
    device = db.scalar(select(Device).where(
        Device.organization_id == context.organization_id,
        Device.code == payload.device_id,
        Device.deleted_at.is_(None),
    ))
    if device is None:
        raise api_error(404, "NOT_FOUND", "设备不存在")
    existing = db.scalar(select(AuditLog).where(
        AuditLog.organization_id == context.organization_id,
        AuditLog.entity_type == "agent_run",
        AuditLog.entity_id == payload.run_id,
    ))
    if existing:
        if existing.after.get("deviceId") != payload.device_id:
            raise api_error(409, "CONFLICT", "Agent 运行编号已关联其他设备")
        return {"id": str(existing.id), "runId": str(payload.run_id), "recorded": True}
    entry = write_audit(
        db, organization_id=context.organization_id, actor_user_id=context.user_id,
        action="agent.assist", entity_type="agent_run", entity_id=payload.run_id,
        after={
            "deviceId": payload.device_id, "status": payload.status,
            "diagnosisStatus": payload.diagnosis_status, "isDemo": payload.is_demo,
            "tools": [tool.model_dump() for tool in payload.tools],
        },
    )
    db.commit()
    db.refresh(entry)
    return {"id": str(entry.id), "runId": str(payload.run_id), "recorded": True}

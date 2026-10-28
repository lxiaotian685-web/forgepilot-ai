from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends

from app.api.context import RequestContext, get_request_context
from app.core.device_provider import DeviceAuth
from app.deps import get_rag
from app.schemas.agent import AgentRequest, AgentResponse
from app.services.agent import AgentService, build_history_tool
from app.services.agent_audit import build_agent_audit_tool
from app.services.rag import RAGService

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/assist", response_model=AgentResponse)
def assist(
    payload: AgentRequest,
    context: RequestContext = Depends(get_request_context),
    rag: RAGService = Depends(get_rag),
):
    history = build_history_tool()
    audit = build_agent_audit_tool()
    try:
        auth = DeviceAuth(
            token=context.token,
            organization_id=context.organization_id,
            user_id=context.user_id,
        )
        result = AgentService(rag, history).assist(
            payload,
            auth,
        )
        if result.status != "unavailable":
            try:
                result.audit_id = audit.record(result, auth)
                result.audit_status = "recorded"
            except (httpx.HTTPError, RuntimeError, ValueError):
                result.audit_status = "unavailable"
        return result
    finally:
        history.close()
        audit.close()

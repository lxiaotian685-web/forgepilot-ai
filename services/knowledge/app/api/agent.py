from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.context import RequestContext, get_request_context
from app.core.device_provider import DeviceAuth
from app.deps import get_rag
from app.schemas.agent import AgentRequest, AgentResponse
from app.services.agent import AgentService, build_history_tool
from app.services.rag import RAGService

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/assist", response_model=AgentResponse)
def assist(
    payload: AgentRequest,
    context: RequestContext = Depends(get_request_context),
    rag: RAGService = Depends(get_rag),
):
    history = build_history_tool()
    try:
        return AgentService(rag, history).assist(
            payload,
            DeviceAuth(
                token=context.token,
                organization_id=context.organization_id,
                user_id=context.user_id,
            ),
        )
    finally:
        history.close()

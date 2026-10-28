from __future__ import annotations

import os

import httpx

from app.core.device_provider import DeviceAuth, DeviceProviderError
from app.schemas.agent import AgentRequest, AgentResponse, HistoryOrder, ToolStep
from app.services.rag import RAGService


class WorkOrderHistoryTool:
    """Read-only B service tool; the caller's identity is forwarded per request."""

    def __init__(self, base_url: str, client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self._client = client or httpx.Client(timeout=5, trust_env=False)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def read(self, device_id: str, auth: DeviceAuth) -> list[HistoryOrder]:
        if not self.base_url:
            raise RuntimeError("未配置工单历史服务")
        if not auth.token or not auth.organization_id:
            raise RuntimeError("工单历史查询需要当前登录身份")
        response = self._client.get(
            f"{self.base_url}/api/v1/work-orders",
            params={"deviceId": device_id, "page": 1, "pageSize": 5},
            headers={
                "Authorization": f"Bearer {auth.token}",
                "X-Organization-Id": auth.organization_id,
                **({"X-User-Id": auth.user_id} if auth.user_id else {}),
            },
        )
        if response.status_code != 200:
            raise RuntimeError("工单历史服务未返回可用数据")
        payload = response.json()
        if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
            raise RuntimeError("工单历史响应格式错误")
        orders = []
        for item in payload["items"]:
            if not isinstance(item, dict) or item.get("deviceId") != device_id:
                raise RuntimeError("工单历史设备身份不一致")
            orders.append(HistoryOrder(
                id=str(item["id"]), device_id=device_id,
                title=str(item["title"]), status=str(item["status"]),
            ))
        return orders


class AgentService:
    """Fixed, auditable read-only tool sequence; diagnosis and writes need human review."""

    def __init__(self, rag: RAGService, history: WorkOrderHistoryTool):
        self.rag = rag
        self.history = history

    def assist(self, request: AgentRequest, auth: DeviceAuth) -> AgentResponse:
        steps: list[ToolStep] = []
        try:
            device = self.rag.device_provider.get_device(request.device_id, auth=auth)
            if device.device_id != request.device_id:
                raise DeviceProviderError("device_mismatch", "设备身份不一致")
        except DeviceProviderError as exc:
            steps.append(ToolStep(name="device_lookup", status="unavailable", summary=exc.message))
            steps.extend([
                ToolStep(name="work_order_history", status="skipped", summary="设备校验失败"),
                ToolStep(name="evidence_diagnosis", status="skipped", summary="设备校验失败"),
            ])
            return AgentResponse(device_id=request.device_id, status="unavailable", tools=steps)
        steps.append(ToolStep(name="device_lookup", status="ok", summary=f"已校验设备 {device.device_id}", count=1))

        history: list[HistoryOrder] = []
        try:
            history = self.history.read(request.device_id, auth)
            steps.append(ToolStep(name="work_order_history", status="ok", summary="已读取同设备历史工单", count=len(history)))
        except (httpx.HTTPError, RuntimeError, KeyError, ValueError) as exc:
            steps.append(ToolStep(name="work_order_history", status="unavailable", summary=f"历史工单不可用：{exc}"))

        diagnosis = self.rag.diagnose(
            device_id=request.device_id, question=request.question,
            equipment_model=request.equipment_model, auth=auth,
        )
        usable = diagnosis.status == "ok" and bool(diagnosis.sources)
        steps.append(ToolStep(
            name="evidence_diagnosis", status="ok" if usable else "unavailable",
            summary="已生成带引用的待人工复核建议" if usable else f"证据诊断状态：{diagnosis.status}",
            count=len(diagnosis.sources),
        ))
        return AgentResponse(
            device_id=request.device_id,
            status="ready_for_review" if usable else "needs_evidence",
            diagnosis=diagnosis, history=history, tools=steps,
            is_demo=diagnosis.is_demo or diagnosis.is_mock,
        )


def build_history_tool() -> WorkOrderHistoryTool:
    return WorkOrderHistoryTool(os.getenv("BUSINESS_API_BASE_URL", ""))

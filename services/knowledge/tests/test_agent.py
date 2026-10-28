from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from app.core.device_provider import (
    DeviceAuth,
    DeviceProviderError,
    StaticDeviceProvider,
)
from app.core.store import KnowledgeBase
from app.llm.mock import MockLLM
from app.main import app
from app.schemas.agent import AgentRequest
from app.services.agent import AgentService, WorkOrderHistoryTool
from app.services.rag import RAGService


def _rag():
    kb = KnowledgeBase()
    kb.ingest(
        title="虚构空压机检修规程", equipment_model="compressor-002",
        organization_id="demo-org", content="排气温度过高时检查冷却器和油位。",
    )
    return RAGService(kb, MockLLM(), StaticDeviceProvider())


def _history(handler):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return WorkOrderHistoryTool("https://business.test", client=client)


def test_agent_reads_only_same_device_history_and_grounded_diagnosis():
    def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/api/v1/work-orders"
        assert request.url.params["deviceId"] == "AC-07"
        assert request.headers["Authorization"] == "Bearer current-token"
        assert request.headers["X-Organization-Id"] == "demo-org"
        return httpx.Response(200, json={"items": [
            {"id": "WO-1", "deviceId": "AC-07", "title": "检查轴承", "status": "已完成"},
        ]})

    response = AgentService(_rag(), _history(handler)).assist(
        AgentRequest(device_id="AC-07", question="排气温度过高怎么办？"),
        DeviceAuth(token="current-token", organization_id="demo-org", user_id="user-1"),
    )
    assert response.status == "ready_for_review"
    assert response.diagnosis.sources
    assert [step.name for step in response.tools] == [
        "device_lookup", "work_order_history", "evidence_diagnosis",
    ]
    assert response.history[0].id == "WO-1"
    assert response.requires_human_confirmation and not response.can_create_work_order


def test_agent_rejects_cross_device_history_instead_of_displaying_it():
    history = _history(lambda _request: httpx.Response(200, json={"items": [
        {"id": "WO-OTHER", "deviceId": "P-102", "title": "其他设备", "status": "已完成"},
    ]}))
    response = AgentService(_rag(), history).assist(
        AgentRequest(device_id="AC-07", question="排气温度过高"),
        DeviceAuth(token="token", organization_id="demo-org"),
    )
    assert response.history == []
    assert response.tools[1].status == "unavailable"


def test_agent_stops_before_history_when_device_is_unauthorized():
    class DeniedProvider:
        def get_device(self, _device_id, auth=None):
            raise DeviceProviderError("device_unauthorized", "无权读取设备")

    rag = _rag()
    rag.device_provider = DeniedProvider()
    response = AgentService(rag, _history(lambda _: (_ for _ in ()).throw(AssertionError("history called")))).assist(
        AgentRequest(device_id="AC-07", question="排气温度过高"),
        DeviceAuth(token="token", organization_id="demo-org"),
    )
    assert response.status == "unavailable"
    assert response.diagnosis is None
    assert [step.status for step in response.tools] == ["unavailable", "skipped", "skipped"]


def test_agent_endpoint_exposes_read_only_contract(monkeypatch):
    monkeypatch.delenv("BUSINESS_API_BASE_URL", raising=False)
    client = TestClient(app)
    result = client.post(
        "/api/v1/agent/assist", json={"device_id": "AC-07", "question": "排气温度过高"},
        headers={"X-Organization-Id": "demo-org"},
    )
    assert result.status_code == 200
    payload = result.json()
    assert payload["device_id"] == "AC-07"
    assert payload["requires_human_confirmation"] is True
    assert payload["can_create_work_order"] is False
    assert payload["tools"][1]["status"] == "unavailable"

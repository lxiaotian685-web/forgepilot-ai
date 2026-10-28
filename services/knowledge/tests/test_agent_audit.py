from __future__ import annotations

import httpx

from app.core.device_provider import DeviceAuth
from app.schemas.agent import AgentResponse, ToolStep
from app.services.agent_audit import AgentAuditTool


def _result():
    return AgentResponse(
        device_id="AC-07", status="needs_evidence", is_demo=True,
        tools=[ToolStep(name="device_lookup", status="ok", summary="private detail", count=1)],
    )


def test_audit_tool_forwards_identity_and_only_sanitized_step_metadata(monkeypatch):
    monkeypatch.setenv("BUSINESS_WRITE_KEY", "write-secret")

    def handler(request):
        assert request.method == "POST"
        assert request.url.path == "/api/v1/agent-runs/audit"
        assert request.headers["Authorization"] == "Bearer current-token"
        assert request.headers["X-Agent-Audit-Key"] == "agent-secret"
        assert request.headers["X-Write-Key"] == "write-secret"
        body = __import__("json").loads(request.content)
        assert body["deviceId"] == "AC-07"
        assert body["tools"] == [{"name": "device_lookup", "status": "ok", "count": 1}]
        assert "private detail" not in str(body)
        return httpx.Response(201, json={"id": "audit-1", "runId": body["runId"], "recorded": True})

    tool = AgentAuditTool("https://business.test", "agent-secret", httpx.Client(transport=httpx.MockTransport(handler)))
    assert tool.record(_result(), DeviceAuth(token="current-token", organization_id="demo-org", user_id="user-1")) == "audit-1"


def test_audit_tool_never_claims_success_without_config_or_valid_reply():
    auth = DeviceAuth(token="current-token", organization_id="demo-org")
    try:
        AgentAuditTool("", "").record(_result(), auth)
    except RuntimeError as error:
        assert "未配置" in str(error)
    else:
        raise AssertionError("missing audit config accepted")
    tool = AgentAuditTool("https://business.test", "agent-secret", httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(503))))
    try:
        tool.record(_result(), auth)
    except RuntimeError as error:
        assert "503" in str(error)
    else:
        raise AssertionError("failed audit write accepted")

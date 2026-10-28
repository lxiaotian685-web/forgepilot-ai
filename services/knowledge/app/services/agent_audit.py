from __future__ import annotations

import os
import uuid

import httpx

from app.core.device_provider import DeviceAuth
from app.schemas.agent import AgentResponse


class AgentAuditTool:
    def __init__(self, base_url: str, secret: str, client: httpx.Client | None = None):
        self.base_url = base_url.rstrip("/")
        self.secret = secret
        self._client = client or httpx.Client(timeout=5, trust_env=False)
        self._owns_client = client is None

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def record(self, result: AgentResponse, auth: DeviceAuth) -> str:
        if not self.base_url or not self.secret:
            raise RuntimeError("Agent 审计服务尚未配置")
        if not auth.token or not auth.organization_id:
            raise RuntimeError("Agent 审计需要当前登录身份")
        run_id = str(uuid.uuid4())
        headers = {
            "Authorization": f"Bearer {auth.token}",
            "X-Organization-Id": auth.organization_id,
            "X-Agent-Audit-Key": self.secret,
        }
        write_key = os.getenv("BUSINESS_WRITE_KEY", "")
        if write_key:
            headers["X-Write-Key"] = write_key
        if auth.user_id:
            headers["X-User-Id"] = auth.user_id
        response = self._client.post(
            f"{self.base_url}/api/v1/agent-runs/audit", headers=headers,
            json={
                "runId": run_id, "deviceId": result.device_id,
                "status": result.status,
                "diagnosisStatus": result.diagnosis.status if result.diagnosis else None,
                "isDemo": result.is_demo,
                "tools": [
                    {"name": step.name, "status": step.status, "count": step.count}
                    for step in result.tools
                ],
            },
        )
        if response.status_code not in {200, 201}:
            raise RuntimeError(f"Agent 审计写入失败（HTTP {response.status_code}）")
        payload = response.json()
        if not isinstance(payload, dict) or not payload.get("recorded") or payload.get("runId") != run_id or not payload.get("id"):
            raise RuntimeError("Agent 审计响应格式错误")
        return payload["id"]


def build_agent_audit_tool() -> AgentAuditTool:
    return AgentAuditTool(
        os.getenv("BUSINESS_API_BASE_URL", ""), os.getenv("AGENT_AUDIT_KEY", "")
    )

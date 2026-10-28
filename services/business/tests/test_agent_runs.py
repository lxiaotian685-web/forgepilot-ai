from __future__ import annotations

import uuid

from sqlalchemy import select

from app.auth import issue_token
from app.models import AuditLog


def _payload(device_id="AC-07", run_id=None):
    return {
        "runId": str(run_id or uuid.uuid4()), "deviceId": device_id,
        "status": "ready_for_review", "diagnosisStatus": "ok", "isDemo": True,
        "tools": [
            {"name": "device_lookup", "status": "ok", "count": 1},
            {"name": "work_order_history", "status": "ok", "count": 2},
            {"name": "evidence_diagnosis", "status": "ok", "count": 3},
        ],
    }


def test_agent_audit_requires_user_and_service_key(api, monkeypatch):
    client, _, _ = api
    monkeypatch.setenv("AUTH_SECRET", "test-secret-value-32-characters-long")
    monkeypatch.setenv("AGENT_AUDIT_KEY", "agent-audit-secret-32-characters-long")
    token = issue_token("demo-org", "demo@example.com")
    payload = _payload()
    assert client.post("/api/v1/agent-runs/audit", json=payload).status_code == 401
    assert client.post("/api/v1/agent-runs/audit", json=payload, headers={"Authorization": f"Bearer {token}"}).status_code == 403
    assert client.post("/api/v1/agent-runs/audit", json=payload, headers={"Authorization": f"Bearer {token}", "X-Agent-Audit-Key": "wrong"}).status_code == 403


def test_agent_audit_is_idempotent_and_only_stores_sanitized_steps(api, monkeypatch):
    client, _, sessions = api
    monkeypatch.setenv("AUTH_SECRET", "test-secret-value-32-characters-long")
    monkeypatch.setenv("AGENT_AUDIT_KEY", "agent-audit-secret-32-characters-long")
    token = issue_token("demo-org", "demo@example.com")
    headers = {"Authorization": f"Bearer {token}", "X-Agent-Audit-Key": "agent-audit-secret-32-characters-long"}
    payload = _payload()
    first = client.post("/api/v1/agent-runs/audit", json=payload, headers=headers)
    second = client.post("/api/v1/agent-runs/audit", json=payload, headers=headers)
    assert first.status_code == second.status_code == 201
    assert first.json()["id"] == second.json()["id"]
    with sessions() as db:
        entries = db.scalars(select(AuditLog).where(AuditLog.entity_id == uuid.UUID(payload["runId"]))).all()
        assert len(entries) == 1
        assert entries[0].after["deviceId"] == "AC-07"
        assert "question" not in entries[0].after
        assert "answer" not in entries[0].after
    changed = client.post("/api/v1/agent-runs/audit", json={**payload, "deviceId": "P-102"}, headers=headers)
    assert changed.status_code == 409


def test_agent_audit_rejects_unknown_device(api, monkeypatch):
    client, _, _ = api
    monkeypatch.setenv("AUTH_SECRET", "test-secret-value-32-characters-long")
    monkeypatch.setenv("AGENT_AUDIT_KEY", "agent-audit-secret-32-characters-long")
    token = issue_token("demo-org", "demo@example.com")
    response = client.post("/api/v1/agent-runs/audit", json=_payload("OTHER"), headers={
        "Authorization": f"Bearer {token}", "X-Agent-Audit-Key": "agent-audit-secret-32-characters-long",
    })
    assert response.status_code == 404

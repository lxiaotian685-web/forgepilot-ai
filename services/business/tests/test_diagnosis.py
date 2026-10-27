from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.models import AuditLog, Diagnosis, WorkOrder


def auth(
    ids: dict, org: str = "demo-org", user: str = "demo@example.com"
) -> dict:
    return {
        "X-Organization-Id": str(ids["organizations"][org]),
        "X-User-Id": str(ids["users"][user]),
    }


def create_diagnosis(
    client: TestClient,
    ids: dict,
    device: str = "AC-07",
    alert: str | None = None,
    org: str = "demo-org",
    user: str = "tech@example.com",
):
    payload = {
        "deviceId": device,
        "question": "设备异常，需要诊断",
        "conclusion": "疑似轴承磨损，建议停机检查",
        "riskLevel": "high",
        "confidence": 92.5,
        "modelSource": "demo-model-v1",
        "evidence": {
            "documents": [
                {
                    "name": "demo-manual.pdf",
                    "version": "v1",
                    "page": 12,
                    "score": 0.92,
                }
            ]
        },
    }
    if alert:
        payload["alertId"] = alert
    return client.post(
        "/api/v1/diagnoses",
        json=payload,
        headers=auth(ids, org=org, user=user),
    )


def test_create_and_get_diagnosis_persists_fields(api):
    client, ids, _ = api
    created = create_diagnosis(client, ids)
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "draft"
    assert body["statusLabel"] == "草稿"
    assert body["modelSource"] == "demo-model-v1"
    assert body["riskLevel"] == "高"
    assert body["confidence"] == 92.5
    assert body["evidence"]["documents"][0]["page"] == 12
    assert body["workOrderId"] is None

    fetched = client.get(
        f"/api/v1/diagnoses/{body['id']}", headers=auth(ids)
    )
    assert fetched.status_code == 200
    detail = fetched.json()
    assert detail["id"] == body["id"]
    assert detail["question"] == body["question"]
    assert detail["conclusion"] == body["conclusion"]
    assert detail["status"] == "draft"

    listed = client.get(
        "/api/v1/diagnoses",
        params={"deviceId": "AC-07"},
        headers=auth(ids),
    )
    assert listed.status_code == 200
    assert body["id"] in [item["id"] for item in listed.json()["items"]]


def test_create_diagnosis_rejects_alert_from_other_device(api):
    client, ids, _ = api
    response = create_diagnosis(client, ids, device="AC-07", alert="ALT-0938")
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["alertId"] == "ALT-0938"


def test_confirm_creates_linked_work_order(api):
    client, ids, session_factory = api
    created = create_diagnosis(client, ids, device="AC-07")
    diagnosis_code = created.json()["id"]

    confirmed = client.post(
        f"/api/v1/diagnoses/{diagnosis_code}/confirm",
        headers=auth(ids, user="tech@example.com"),
    )
    assert confirmed.status_code == 200
    body = confirmed.json()
    assert body["diagnosis"]["status"] == "confirmed"
    assert body["diagnosis"]["statusLabel"] == "已确认"
    assert body["diagnosis"]["confirmedBy"] == "张工"
    assert body["diagnosis"]["confirmedAt"] is not None
    assert body["diagnosis"]["workOrderId"] == body["workOrder"]["id"]
    assert body["workOrder"]["deviceId"] == "AC-07"
    assert body["workOrder"]["diagnosisId"] == diagnosis_code
    assert body["workOrder"]["status"] == "待处理"

    with session_factory() as session:
        diagnosis = session.scalar(
            select(Diagnosis).where(Diagnosis.code == diagnosis_code)
        )
        order = session.scalar(
            select(WorkOrder).where(
                WorkOrder.code == body["workOrder"]["id"]
            )
        )
        assert diagnosis.status == "confirmed"
        assert diagnosis.confirmed_by == ids["users"]["tech@example.com"]
        assert order.diagnosis_id == diagnosis.id
        assert order.device_id == diagnosis.device_id

    refreshed = client.get(
        f"/api/v1/diagnoses/{diagnosis_code}", headers=auth(ids)
    )
    assert refreshed.json()["workOrderId"] == body["workOrder"]["id"]


def test_confirm_is_idempotent(api):
    client, ids, session_factory = api
    created = create_diagnosis(client, ids, device="AC-07")
    diagnosis_code = created.json()["id"]

    first = client.post(
        f"/api/v1/diagnoses/{diagnosis_code}/confirm",
        headers=auth(ids, user="tech@example.com"),
    )
    second = client.post(
        f"/api/v1/diagnoses/{diagnosis_code}/confirm",
        headers=auth(ids, user="tech@example.com"),
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert (
        first.json()["workOrder"]["id"]
        == second.json()["workOrder"]["id"]
    )

    with session_factory() as session:
        diagnosis = session.scalar(
            select(Diagnosis).where(Diagnosis.code == diagnosis_code)
        )
        orders = session.scalars(
            select(WorkOrder).where(
                WorkOrder.diagnosis_id == diagnosis.id
            )
        ).all()
        confirm_audits = session.scalars(
            select(AuditLog).where(
                AuditLog.action == "diagnosis.confirm",
                AuditLog.entity_id == diagnosis.id,
            )
        ).all()
        assert len(orders) == 1
        assert len(confirm_audits) == 1


def test_confirm_cross_org_rejected(api):
    client, ids, session_factory = api
    created = create_diagnosis(
        client,
        ids,
        device="NV-01",
        org="northwind-org",
        user="other@example.com",
    )
    assert created.status_code == 201
    diagnosis_code = created.json()["id"]

    response = client.post(
        f"/api/v1/diagnoses/{diagnosis_code}/confirm",
        headers=auth(ids, user="tech@example.com"),
    )
    assert response.status_code == 404

    with session_factory() as session:
        diagnosis = session.scalar(
            select(Diagnosis).where(Diagnosis.code == diagnosis_code)
        )
        orders = session.scalars(
            select(WorkOrder).where(
                WorkOrder.diagnosis_id == diagnosis.id
            )
        ).all()
        assert diagnosis.status == "draft"
        assert orders == []


def test_work_order_requires_confirmed_diagnosis(api):
    client, ids, _ = api
    response = client.post(
        "/api/v1/work-orders",
        json={
            "title": "未确认诊断建单",
            "deviceId": "P-102",
            "diagnosisId": "DIAG-20250518-0938",
        },
        headers=auth(ids, user="manager@example.com"),
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "INVALID_STATE"
    assert error["details"]["diagnosisId"] == "DIAG-20250518-0938"


def test_work_order_rejects_cross_device_diagnosis(api):
    client, ids, _ = api
    response = client.post(
        "/api/v1/work-orders",
        json={
            "title": "跨设备诊断建单",
            "deviceId": "P-102",
            "diagnosisId": "DIAG-20250518-0941",
        },
        headers=auth(ids, user="manager@example.com"),
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["diagnosisId"] == "DIAG-20250518-0941"


def test_confirm_rolls_back_on_failure(api, monkeypatch):
    client, ids, session_factory = api
    diagnosis_code = "DIAG-20250518-0938"

    def boom(*args, **kwargs):
        raise RuntimeError("audit failure")

    monkeypatch.setattr("app.api.diagnoses.write_audit", boom)
    with pytest.raises(RuntimeError):
        client.post(
            f"/api/v1/diagnoses/{diagnosis_code}/confirm",
            headers=auth(ids, user="tech@example.com"),
        )

    with session_factory() as session:
        diagnosis = session.scalar(
            select(Diagnosis).where(Diagnosis.code == diagnosis_code)
        )
        orders = session.scalars(
            select(WorkOrder).where(
                WorkOrder.diagnosis_id == diagnosis.id
            )
        ).all()
        assert diagnosis.status == "draft"
        assert diagnosis.confirmed_at is None
        assert diagnosis.confirmed_by is None
        assert orders == []


def test_diagnosis_write_requires_technician(api):
    client, ids, _ = api
    denied_create = create_diagnosis(
        client, ids, device="AC-07", user="viewer@example.com"
    )
    assert denied_create.status_code == 403

    denied_confirm = client.post(
        "/api/v1/diagnoses/DIAG-20250518-0938/confirm",
        headers=auth(ids, user="viewer@example.com"),
    )
    assert denied_confirm.status_code == 403


def test_audit_events_requires_manager(api):
    client, ids, _ = api
    for user in ("viewer@example.com", "tech@example.com"):
        response = client.get(
            "/api/v1/audit-events", headers=auth(ids, user=user)
        )
        assert response.status_code == 403
    allowed = client.get(
        "/api/v1/audit-events", headers=auth(ids, user="manager@example.com")
    )
    assert allowed.status_code == 200
    assert allowed.json()["total"] >= 2


def test_audit_events_org_isolation(api):
    client, ids, _ = api
    demo = client.get(
        "/api/v1/audit-events", headers=auth(ids, user="manager@example.com")
    )
    assert demo.json()["total"] >= 2
    north = client.get(
        "/api/v1/audit-events",
        headers=auth(ids, org="northwind-org", user="other@example.com"),
    )
    assert north.status_code == 200
    assert north.json()["total"] == 0


def test_audit_events_records_confirmation_and_work_order(api):
    client, ids, _ = api
    created = create_diagnosis(client, ids, device="AC-07")
    diagnosis_code = created.json()["id"]
    client.post(
        f"/api/v1/diagnoses/{diagnosis_code}/confirm",
        headers=auth(ids, user="tech@example.com"),
    )

    confirmations = client.get(
        "/api/v1/audit-events",
        params={"action": "diagnosis.confirm"},
        headers=auth(ids, user="manager@example.com"),
    )
    assert confirmations.status_code == 200
    items = confirmations.json()["items"]
    assert len(items) >= 1
    entry = items[0]
    assert entry["action"] == "diagnosis.confirm"
    assert entry["entityType"] == "diagnosis"
    assert entry["user"] == "张工"
    assert entry["result"] == "成功"

    orders = client.get(
        "/api/v1/work-orders",
        params={"deviceId": "AC-07"},
        headers=auth(ids),
    )
    work_order = next(
        item
        for item in orders.json()["items"]
        if item["diagnosisId"] == diagnosis_code
    )
    assert work_order["deviceId"] == "AC-07"
    assert work_order["diagnosisId"] == diagnosis_code
    assert work_order["alertId"] is None


def test_token_mode_requires_bearer_and_ignores_headers(api, monkeypatch):
    client, ids, _ = api
    monkeypatch.setenv("AUTH_SECRET", "test-secret-value-32-characters-long")
    monkeypatch.setattr("app.api.deps.AUTH_MODE", "token")

    denied = client.get("/api/v1/devices", headers=auth(ids))
    assert denied.status_code == 401

    from app.auth import issue_token

    token = issue_token("demo-org", "demo@example.com")
    allowed = client.get(
        "/api/v1/devices",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert allowed.status_code == 200

    forged = client.get(
        "/api/v1/devices",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": str(ids["organizations"]["northwind-org"]),
            "X-User-Id": str(ids["users"]["other@example.com"]),
        },
    )
    assert forged.status_code == 200
    assert "AC-07" in {item["id"] for item in forged.json()["items"]}


def test_write_protection_requires_key(api, monkeypatch):
    client, ids, _ = api
    monkeypatch.setattr("app.main.WRITE_API_KEY", "write-secret")
    payload = {"title": "写入保护测试", "deviceId": "AC-07"}

    denied = client.post(
        "/api/v1/work-orders",
        json=payload,
        headers=auth(ids, user="manager@example.com"),
    )
    assert denied.status_code == 403

    allowed = client.post(
        "/api/v1/work-orders",
        json=payload,
        headers={
            **auth(ids, user="manager@example.com"),
            "X-Write-Key": "write-secret",
        },
    )
    assert allowed.status_code == 201


def test_token_round_trip_and_expiry(monkeypatch):
    monkeypatch.setenv("AUTH_SECRET", "test-secret-value-32-characters-long")
    from app.auth import issue_token, verify_token

    token = issue_token("demo-org", "demo@example.com")
    payload = verify_token(token)
    assert payload is not None
    assert payload["org"] == "demo-org"
    assert payload["user"] == "demo@example.com"

    expired = issue_token("demo-org", "demo@example.com", ttl_seconds=-1)
    assert verify_token(expired) is None

    body, signature = token.split(".", 1)
    tampered_body = ("A" if body[0] != "A" else "B") + body[1:]
    assert verify_token(f"{tampered_body}.{signature}") is None


def test_device_query_adapter_is_authoritative(api):
    _, ids, session_factory = api
    from app.services.device_query import get_device_facts, list_device_facts

    with session_factory() as session:
        facts = get_device_facts(
            session, ids["organizations"]["demo-org"], "AC-07"
        )
        assert facts is not None
        assert facts["model"] == "GX11"
        parameters = {item["name"]: item for item in facts["parameters"]}
        assert parameters["rated_power"]["source"] == "nameplate"
        assert parameters["vibration"]["unit"] == "mm/s"
        assert parameters["vibration"]["source"] == "sensor"

        assert (
            get_device_facts(
                session, ids["organizations"]["northwind-org"], "AC-07"
            )
            is None
        )
        listed = list_device_facts(
            session, ids["organizations"]["demo-org"]
        )
        assert "AC-07" in [device["id"] for device in listed]

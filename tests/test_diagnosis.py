from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.models import AuditLog, Diagnosis, WorkOrder
from app.seed import seed_demo


@pytest.fixture()
def api():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    with testing_session() as session:
        ids = seed_demo(session)

    def override_get_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, ids, testing_session
    app.dependency_overrides.clear()


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

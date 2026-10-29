from __future__ import annotations

from sqlalchemy import select

from app.models import AuditLog, MaintenanceRecord, WorkOrder


def auth(
    ids: dict, org: str = "demo-org", user: str = "demo@example.com"
) -> dict:
    return {
        "X-Organization-Id": str(ids["organizations"][org]),
        "X-User-Id": str(ids["users"][user]),
    }


def test_completed_work_order_writes_history(api):
    client, ids, session_factory = api
    headers = auth(ids, user="tech@example.com")

    to_verifying = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "待验收"},
        headers=headers,
    )
    assert to_verifying.status_code == 200
    missing_action = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "已完成"},
        headers=auth(ids, user="manager@example.com"),
    )
    assert missing_action.status_code == 422
    completed = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "已完成", "rootCause": "轴承磨损", "actionTaken": "更换轴承并复测振动"},
        headers=auth(ids, user="manager@example.com"),
    )
    assert completed.status_code == 200

    history = client.get(
        "/api/v1/maintenance-records",
        params={"deviceId": "AC-07"},
        headers=auth(ids, user="viewer@example.com"),
    )
    assert history.status_code == 200
    record = next(
        item
        for item in history.json()["items"]
        if item["workOrderId"] == "WO-20250518-01"
    )
    assert record["deviceId"] == "AC-07"
    assert record["diagnosisId"] == "DIAG-20250518-0941"
    assert record["alertId"] == "ALT-0941"
    assert record["recordType"] == "维护"
    assert record["recordedBy"]
    assert "AC-07" in record["summary"]
    assert record["rootCause"] == "轴承磨损"
    assert record["actionTaken"] == "更换轴承并复测振动"

    with session_factory() as session:
        order = session.scalar(
            select(WorkOrder).where(WorkOrder.code == "WO-20250518-01")
        )
        records = session.scalars(
            select(MaintenanceRecord).where(
                MaintenanceRecord.work_order_id == order.id
            )
        ).all()
        assert len(records) == 1
        audit = session.scalar(
            select(AuditLog).where(
                AuditLog.action == "maintenance_record.create"
            )
        )
        assert audit is not None


def test_repeated_completion_keeps_single_history(api):
    client, ids, session_factory = api
    headers = auth(ids, user="tech@example.com")
    client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "待验收"},
        headers=headers,
    )
    client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "已完成", "actionTaken": "更换轴承并复测振动"},
        headers=auth(ids, user="manager@example.com"),
    )
    again = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "已完成"},
        headers=auth(ids, user="manager@example.com"),
    )
    assert again.status_code == 200

    with session_factory() as session:
        order = session.scalar(
            select(WorkOrder).where(WorkOrder.code == "WO-20250518-01")
        )
        records = session.scalars(
            select(MaintenanceRecord).where(
                MaintenanceRecord.work_order_id == order.id
            )
        ).all()
        assert len(records) == 1


def test_seeded_completed_work_order_has_history(api):
    client, ids, _ = api
    response = client.get(
        "/api/v1/maintenance-records",
        params={"workOrderId": "WO-20250516-04"},
        headers=auth(ids),
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    assert items[0]["deviceId"] == "AC-08"
    assert items[0]["alertId"] == "ALT-0911"


def test_device_history_cross_org_isolation(api):
    client, ids, _ = api
    north = client.get(
        "/api/v1/maintenance-records",
        params={"deviceId": "AC-08"},
        headers=auth(ids, org="northwind-org", user="other@example.com"),
    )
    assert north.status_code == 200
    assert north.json()["total"] == 0

    demo = client.get(
        "/api/v1/maintenance-records",
        params={"deviceId": "AC-08"},
        headers=auth(ids, user="viewer@example.com"),
    )
    assert demo.status_code == 200
    assert demo.json()["total"] >= 1

from __future__ import annotations

from sqlalchemy import select

from app.models import AuditLog, Device, utcnow
from app.seed import USER_OTHER_ID


def auth(ids: dict, org: str = "demo-org", user: str = "demo@example.com") -> dict:
    return {
        "X-Organization-Id": str(ids["organizations"][org]),
        "X-User-Id": str(ids["users"][user]),
    }


def test_devices_list_aligns_with_frontend(api):
    client, ids, _ = api
    response = client.get("/api/v1/devices", headers=auth(ids))

    assert response.status_code == 200
    body = response.json()
    assert {"items", "page", "pageSize", "total", "totalPages"} <= body.keys()
    device = next(item for item in body["items"] if item["id"] == "AC-07")
    assert {
        "id",
        "name",
        "type",
        "location",
        "health",
        "state",
        "alert",
    } <= device.keys()
    assert device["name"] == "螺杆空气压缩机"
    assert device["state"] in {"运行正常", "需关注", "告警异常", "离线"}
    assert device["alert"] == 1
    assert isinstance(device["health"], float)


def test_device_detail_and_org_isolation(api):
    client, ids, _ = api
    response = client.get("/api/v1/devices/AC-07", headers=auth(ids))

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "AC-07"
    assert body["plantId"] == "PLANT-SH-01"
    assert body["serialNumber"] == "SN-DEMO-0007"

    other = client.get(
        "/api/v1/devices/AC-07",
        headers=auth(ids, org="northwind-org", user="other@example.com"),
    )
    assert other.status_code == 404
    assert other.json()["error"]["code"] == "NOT_FOUND"


def test_device_filter_and_pagination(api):
    client, ids, _ = api
    filtered = client.get(
        "/api/v1/devices",
        params={"state": "告警异常"},
        headers=auth(ids),
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["items"]] == ["CNC-04"]

    paged = client.get(
        "/api/v1/devices",
        params={"page": 1, "pageSize": 2},
        headers=auth(ids),
    )
    body = paged.json()
    assert len(body["items"]) == 2
    assert body["total"] >= 6
    assert body["pageSize"] == 2


def test_page_size_limit_returns_validation_error(api):
    client, ids, _ = api
    response = client.get(
        "/api/v1/devices", params={"pageSize": 101}, headers=auth(ids)
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_acknowledge_alert_and_idempotency(api):
    client, ids, session_factory = api
    response = client.post(
        "/api/v1/alerts/ALT-0941/acknowledge",
        json={"note": "已到现场核实"},
        headers=auth(ids, user="tech@example.com"),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "已确认"
    assert response.json()["owner"] == "张工"

    again = client.post(
        "/api/v1/alerts/ALT-0941/acknowledge",
        headers=auth(ids, user="tech@example.com"),
    )
    assert again.status_code == 200
    assert again.json()["status"] == "已确认"

    with session_factory() as session:
        entries = session.scalars(
            select(AuditLog).where(AuditLog.action == "alert.acknowledge")
        ).all()
        notes = [
            entry.after.get("note")
            for entry in entries
            if isinstance(entry.after, dict)
        ]
        assert "已到现场核实" in notes


def test_acknowledge_requires_technician(api):
    client, ids, _ = api
    response = client.post(
        "/api/v1/alerts/ALT-0941/acknowledge",
        headers=auth(ids, user="viewer@example.com"),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


def test_acknowledge_closed_alert_conflict(api):
    client, ids, _ = api
    response = client.post(
        "/api/v1/alerts/ALT-0911/acknowledge",
        headers=auth(ids, user="tech@example.com"),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "INVALID_STATE"


def test_alerts_list_fields(api):
    client, ids, _ = api
    response = client.get("/api/v1/alerts", headers=auth(ids))
    assert response.status_code == 200
    alert = next(
        item for item in response.json()["items"] if item["id"] == "ALT-0941"
    )
    assert alert["device"] == "AC-07 螺杆空气压缩机"
    assert alert["level"] == "一级紧急"
    assert alert["status"] == "待确认"
    assert {"id", "level", "title", "device", "time", "owner", "status"} <= alert.keys()


def test_create_work_order_permission_and_success(api):
    client, ids, session_factory = api
    payload = {"title": "AC-07 轴承复检", "deviceId": "AC-07", "priority": "P2 高"}

    denied = client.post(
        "/api/v1/work-orders",
        json=payload,
        headers=auth(ids, user="tech@example.com"),
    )
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "FORBIDDEN"

    created = client.post(
        "/api/v1/work-orders",
        json=payload,
        headers=auth(ids, user="manager@example.com"),
    )
    assert created.status_code == 201
    body = created.json()
    assert body["id"].startswith("WO-")
    assert body["status"] == "待处理"
    assert body["priority"] == "P2 高"
    assert body["deviceId"] == "AC-07"

    with session_factory() as session:
        entry = session.scalar(
            select(AuditLog).where(AuditLog.action == "work_order.create")
        )
        assert entry is not None


def test_create_work_order_unknown_device(api):
    client, ids, _ = api
    response = client.post(
        "/api/v1/work-orders",
        json={"title": "无效设备", "deviceId": "NOPE"},
        headers=auth(ids, user="manager@example.com"),
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


def test_work_order_cannot_be_assigned_to_read_only_member(api):
    client, ids, _ = api
    viewer_id = str(ids["users"]["viewer@example.com"])
    created = client.post(
        "/api/v1/work-orders",
        json={"title": "不能指派访客", "deviceId": "AC-07", "ownerId": viewer_id},
        headers=auth(ids, user="manager@example.com"),
    )
    assert created.status_code == 422
    updated = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"ownerId": viewer_id},
        headers=auth(ids, user="manager@example.com"),
    )
    assert updated.status_code == 422


def test_create_work_order_rejects_alert_from_other_device(api):
    client, ids, _ = api
    response = client.post(
        "/api/v1/work-orders",
        json={
            "title": "跨设备告警工单",
            "deviceId": "AC-07",
            "alertId": "ALT-0938",
        },
        headers=auth(ids, user="manager@example.com"),
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["alertId"] == "ALT-0938"
    assert error["details"]["deviceId"] == "AC-07"


def test_create_work_order_rejects_diagnosis_from_other_device(api):
    client, ids, _ = api
    response = client.post(
        "/api/v1/work-orders",
        json={
            "title": "跨设备诊断工单",
            "deviceId": "AC-07",
            "diagnosisId": "DIAG-20250518-0938",
        },
        headers=auth(ids, user="manager@example.com"),
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR"
    assert error["details"]["diagnosisId"] == "DIAG-20250518-0938"
    assert error["details"]["deviceId"] == "AC-07"


def test_create_work_order_rejects_duplicate_diagnosis_work_order(api):
    client, ids, _ = api
    response = client.post(
        "/api/v1/work-orders",
        json={
            "title": "AC-07 关联告警与诊断",
            "deviceId": "AC-07",
            "alertId": "ALT-0941",
            "diagnosisId": "DIAG-20250518-0941",
        },
        headers=auth(ids, user="manager@example.com"),
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "CONFLICT"
    assert error["details"]["workOrderId"] == "WO-20250518-01"


def test_work_order_patch_transitions(api):
    client, ids, _ = api
    headers = auth(ids, user="tech@example.com")

    to_verifying = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "待验收"},
        headers=headers,
    )
    assert to_verifying.status_code == 200
    assert to_verifying.json()["status"] == "待验收"

    denied_completion = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "已完成"},
        headers=headers,
    )
    assert denied_completion.status_code == 403

    to_completed = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "已完成"},
        headers=auth(ids, user="manager@example.com"),
    )
    assert to_completed.status_code == 200
    assert to_completed.json()["status"] == "已完成"

    invalid = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "处理中"},
        headers=headers,
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_TRANSITION"


def test_work_order_patch_rejects_cross_org_owner(api):
    client, ids, _ = api
    response = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"ownerId": str(USER_OTHER_ID)},
        headers=auth(ids, user="manager@example.com"),
    )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_technician_cannot_edit_or_cancel_order(api):
    client, ids, _ = api
    headers = auth(ids, user="tech@example.com")
    for body in ({"title": "擅自改名"}, {"ownerId": str(ids["users"]["manager@example.com"])}, {"status": "已取消", "cancelReason": "无"}):
        response = client.patch("/api/v1/work-orders/WO-20250518-01", json=body, headers=headers)
        assert response.status_code == 403
    missing_reason = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "已取消"},
        headers=auth(ids, user="manager@example.com"),
    )
    assert missing_reason.status_code == 422


def test_cross_org_work_order_patch_not_found(api):
    client, ids, _ = api
    response = client.patch(
        "/api/v1/work-orders/WO-20250518-01",
        json={"status": "处理中"},
        headers=auth(ids, org="northwind-org", user="other@example.com"),
    )
    assert response.status_code == 404


def test_soft_deleted_device_hidden(api):
    client, ids, session_factory = api
    with session_factory() as session:
        device = session.scalar(select(Device).where(Device.code == "CV-01"))
        device.deleted_at = utcnow()
        session.commit()

    listing = client.get("/api/v1/devices", headers=auth(ids))
    assert "CV-01" not in [item["id"] for item in listing.json()["items"]]

    detail = client.get("/api/v1/devices/CV-01", headers=auth(ids))
    assert detail.status_code == 404

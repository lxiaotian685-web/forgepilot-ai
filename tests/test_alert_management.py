from sqlalchemy import select

from app.models import AuditLog


def auth(ids, org="demo-org", user="demo@example.com"):
    return {
        "X-Organization-Id": str(ids["organizations"][org]),
        "X-User-Id": str(ids["users"][user]),
    }


def test_create_assign_process_and_close_alert(api):
    client, ids, session_factory = api
    manager = auth(ids, user="manager@example.com")
    tech_id = str(ids["users"]["tech@example.com"])
    created = client.post("/api/v1/alerts", json={
        "deviceId": "AC-07", "title": "排气温度异常", "level": "一级紧急",
        "ownerId": tech_id,
    }, headers=manager)
    assert created.status_code == 201
    alert_id = created.json()["id"]
    assert created.json()["ownerId"] == tech_id

    processing = client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "处理中"}, headers=auth(ids, user="tech@example.com"))
    assert processing.status_code == 200
    assert processing.json()["status"] == "处理中"
    closed = client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "已关闭"}, headers=manager)
    assert closed.status_code == 200
    reopened = client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "处理中"}, headers=manager)
    assert reopened.status_code == 200
    with session_factory() as session:
        actions = [entry.action for entry in session.scalars(select(AuditLog).where(AuditLog.entity_type == "alert")).all()]
        assert "alert.create" in actions
        assert "alert.update" in actions


def test_alert_rejects_viewer_assignment_and_illegal_transition(api):
    client, ids, _ = api
    manager = auth(ids, user="manager@example.com")
    viewer = client.post("/api/v1/alerts", json={
        "deviceId": "AC-07", "title": "不应指派访客", "ownerId": str(ids["users"]["viewer@example.com"]),
    }, headers=manager)
    assert viewer.status_code == 422
    created = client.post("/api/v1/alerts", json={"deviceId": "AC-07", "title": "未指派告警"}, headers=manager)
    alert_id = created.json()["id"]
    no_owner = client.patch(f"/api/v1/alerts/{alert_id}", json={"status": "处理中"}, headers=manager)
    assert no_owner.status_code == 422
    outsider = client.patch(f"/api/v1/alerts/{alert_id}", json={"ownerId": str(ids["users"]["other@example.com"])}, headers=manager)
    assert outsider.status_code == 422
    unauthorized = client.post("/api/v1/alerts", json={"deviceId": "AC-07", "title": "无权限"}, headers=auth(ids, user="tech@example.com"))
    assert unauthorized.status_code == 403

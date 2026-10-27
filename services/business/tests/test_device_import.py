from sqlalchemy import select

from app.models import AuditLog, Device


def auth(ids: dict, org: str = "demo-org", user: str = "demo@example.com") -> dict:
    return {
        "X-Organization-Id": str(ids["organizations"][org]),
        "X-User-Id": str(ids["users"][user]),
    }


def row(code: str, plant: str = "上海演示工厂") -> dict:
    return {
        "id": code,
        "name": "演示电机",
        "type": "电机",
        "plant": plant,
        "location": "动力站 Bay01",
    }


def test_batch_import_is_persistent_and_audited(api):
    client, ids, session_factory = api
    response = client.post(
        "/api/v1/devices/import",
        json={"items": [row("M-001"), row("M-002", "PLANT-SH-01")]},
        headers=auth(ids, user="manager@example.com"),
    )
    assert response.status_code == 201
    assert response.json()["created"] == 2
    assert response.json()["items"][0]["health"] is None
    listed = client.get("/api/v1/devices", headers=auth(ids)).json()["items"]
    imported = [item for item in listed if item["id"] == "M-001"]
    assert imported[0]["plant"] == "上海演示工厂"
    assert imported[0]["state"] == "离线"
    with session_factory() as session:
        assert session.scalar(select(Device).where(Device.code == "M-001")) is not None
        assert len(session.scalars(select(AuditLog).where(AuditLog.action == "device.import")).all()) == 2


def test_import_rejects_unauthorized_and_cross_organization_plant(api):
    client, ids, _ = api
    denied = client.post(
        "/api/v1/devices/import", json={"items": [row("M-003")]}, headers=auth(ids, user="tech@example.com")
    )
    assert denied.status_code == 403
    wrong_plant = client.post(
        "/api/v1/devices/import", json={"items": [row("M-003", "北京演示工厂")]}, headers=auth(ids)
    )
    assert wrong_plant.status_code == 422


def test_import_rejects_duplicates_without_partial_save(api):
    client, ids, session_factory = api
    duplicate = client.post(
        "/api/v1/devices/import", json={"items": [row("M-004"), row("m-004")]}, headers=auth(ids)
    )
    assert duplicate.status_code == 422
    existing = client.post(
        "/api/v1/devices/import", json={"items": [row("M-005"), row("AC-07")]}, headers=auth(ids)
    )
    assert existing.status_code == 409
    with session_factory() as session:
        assert session.scalar(select(Device).where(Device.code == "M-005")) is None

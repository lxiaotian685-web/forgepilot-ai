from __future__ import annotations

from sqlalchemy import select

from app.models import AuditLog


def auth(
    ids: dict, org: str = "demo-org", user: str = "demo@example.com"
) -> dict:
    return {
        "X-Organization-Id": str(ids["organizations"][org]),
        "X-User-Id": str(ids["users"][user]),
    }


def test_list_device_parameters(api):
    client, ids, _ = api
    response = client.get(
        "/api/v1/devices/AC-07/parameters", headers=auth(ids)
    )
    assert response.status_code == 200
    items = response.json()["items"]
    names = {item["name"] for item in items}
    assert {"rated_power", "rated_pressure", "vibration", "temperature"} <= names
    rated = next(item for item in items if item["name"] == "rated_power")
    assert rated["source"] == "nameplate"
    assert rated["unit"] == "kW"


def test_list_latest_parameters(api):
    client, ids, _ = api
    response = client.get(
        "/api/v1/devices/AC-07/parameters",
        params={"latest": True},
        headers=auth(ids),
    )
    assert response.status_code == 200
    names = [item["name"] for item in response.json()["items"]]
    assert len(names) == len(set(names))
    assert "vibration" in names


def test_create_update_delete_parameter(api):
    client, ids, session_factory = api
    headers = auth(ids, user="tech@example.com")
    created = client.post(
        "/api/v1/devices/AC-07/parameters",
        json={
            "name": "oil_pressure",
            "value": 0.42,
            "unit": "MPa",
            "source": "sensor",
            "sourceRef": "sensor:AC-07:OIL-01",
            "recordedAt": "2026-10-21T12:00:00+00:00",
        },
        headers=headers,
    )
    assert created.status_code == 201
    parameter = created.json()
    assert parameter["isAuthoritative"] is True
    parameter_id = parameter["id"]

    updated = client.patch(
        f"/api/v1/devices/AC-07/parameters/{parameter_id}",
        json={"value": 0.45, "unit": "bar"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["value"] == 0.45
    assert updated.json()["unit"] == "bar"

    deleted = client.delete(
        f"/api/v1/devices/AC-07/parameters/{parameter_id}",
        headers=auth(ids, user="manager@example.com"),
    )
    assert deleted.status_code == 204

    listed = client.get(
        "/api/v1/devices/AC-07/parameters",
        params={"name": "oil_pressure"},
        headers=auth(ids),
    )
    assert listed.json()["total"] == 0

    with session_factory() as session:
        actions = {
            entry.action for entry in session.scalars(select(AuditLog)).all()
        }
        assert {
            "device_parameter.create",
            "device_parameter.update",
            "device_parameter.delete",
        } <= actions


def test_model_inference_cannot_be_authoritative(api):
    client, ids, _ = api
    response = client.post(
        "/api/v1/devices/AC-07/parameters",
        json={
            "name": "predicted_temp",
            "value": 80,
            "unit": "°C",
            "source": "model_inference",
            "isAuthoritative": True,
            "recordedAt": "2026-10-21T12:00:00+00:00",
        },
        headers=auth(ids, user="tech@example.com"),
    )
    assert response.status_code == 201
    assert response.json()["isAuthoritative"] is False


def test_parameter_write_requires_technician(api):
    client, ids, _ = api
    payload = {
        "name": "viewer_blocked",
        "value": 1,
        "source": "sensor",
        "recordedAt": "2026-10-21T12:00:00+00:00",
    }
    denied = client.post(
        "/api/v1/devices/AC-07/parameters",
        json=payload,
        headers=auth(ids, user="viewer@example.com"),
    )
    assert denied.status_code == 403

    created = client.post(
        "/api/v1/devices/AC-07/parameters",
        json=payload,
        headers=auth(ids, user="tech@example.com"),
    )
    assert created.status_code == 201
    parameter_id = created.json()["id"]
    denied_delete = client.delete(
        f"/api/v1/devices/AC-07/parameters/{parameter_id}",
        headers=auth(ids, user="viewer@example.com"),
    )
    assert denied_delete.status_code == 403


def test_parameter_cross_org_404(api):
    client, ids, _ = api
    north = auth(ids, org="northwind-org", user="other@example.com")
    assert (
        client.get(
            "/api/v1/devices/AC-07/parameters", headers=north
        ).status_code
        == 404
    )
    created = client.post(
        "/api/v1/devices/AC-07/parameters",
        json={
            "name": "cross_org",
            "value": 1,
            "source": "sensor",
            "recordedAt": "2026-10-21T12:00:00+00:00",
        },
        headers=north,
    )
    assert created.status_code == 404


def test_duplicate_parameter_conflict(api):
    client, ids, _ = api
    headers = auth(ids, user="tech@example.com")
    payload = {
        "name": "duplicate_param",
        "value": 1,
        "source": "sensor",
        "recordedAt": "2026-10-21T12:00:00+00:00",
    }
    first = client.post(
        "/api/v1/devices/AC-07/parameters", json=payload, headers=headers
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/devices/AC-07/parameters", json=payload, headers=headers
    )
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "CONFLICT"

from __future__ import annotations

from copy import deepcopy

import pytest
from sqlalchemy import func, select

from app.api import deps, device_parameters
from app.models import AuditLog, DeviceParameter
from tests.test_device_parameters import auth

PATH = "/api/v1/devices/AC-07/parameters/batch"


def payload():
    return {
        "recordedAt": "2026-11-11T14:30:00+08:00",
        "sourceRef": "人工巡检：驱动端轴承",
        "items": [
            {"name": "vibration", "value": 3.2, "unit": "mm/s"},
            {"name": "temperature", "value": 76.5, "unit": "°C"},
        ],
    }


def counts(factory):
    with factory() as db:
        return tuple(
            db.scalar(select(func.count()).select_from(model))
            for model in (DeviceParameter, AuditLog)
        )


def test_batch_success_and_audit(api):
    client, ids, factory = api
    before = counts(factory)
    response = client.post(PATH, json=payload(), headers=auth(ids, user="tech@example.com"))
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["total"] == 2
    assert [item["name"] for item in body["items"]] == ["vibration", "temperature"]
    assert [item["value"] for item in body["items"]] == [3.2, 76.5]
    assert all(item["source"] == "manual" for item in body["items"])
    assert all(item["isAuthoritative"] is True for item in body["items"])
    assert all(item["sourceRef"] == payload()["sourceRef"] for item in body["items"])
    assert counts(factory) == (before[0] + 2, before[1] + 2)
    with factory() as db:
        records = db.scalars(select(DeviceParameter).where(
            DeviceParameter.source_ref == payload()["sourceRef"]
        )).all()
        assert {r.recorded_at.replace(tzinfo=None).isoformat() for r in records} == {
            "2026-11-11T06:30:00"
        }
        logs = db.scalars(select(AuditLog).where(
            AuditLog.entity_id.in_([r.id for r in records])
        )).all()
        assert len(logs) == 2
        assert len({log.after["batchId"] for log in logs}) == 1
        assert all(log.action == "device_parameter.create" for log in logs)
        assert all(log.actor_user_id == ids["users"]["tech@example.com"] for log in logs)
        assert all(log.organization_id == ids["organizations"]["demo-org"] for log in logs)


@pytest.mark.parametrize("change", [
    {"items": []},
    {"items": [{"name": "vibration", "value": 1}] * 101},
    {"items": [{"name": "vibration", "value": 1}, {"name": " vibration ", "value": 2}]},
    {"items": [{"name": "valid", "value": 1}, {"name": "bad", "value": "NaN"}]},
    {"items": [{"name": "bad", "value": "Infinity"}]},
    {"items": [{"name": "bad", "value": 1000000000000}]},
    {"items": [{"name": "bad", "value": "0.1234567"}]},
    {"items": [{"name": " ", "value": 1}]},
    {"items": [{"name": "x", "value": 1, "source": "sensor"}]},
    {"recordedAt": "2026-11-11T14:30:00"},
    {"recordedAt": "invalid"},
    {"recordedAt": None},
    {"sourceRef": " "},
    {"source": "model_inference"},
])
def test_invalid_batch_writes_nothing(api, change):
    client, ids, factory = api
    before = counts(factory)
    request = payload() | deepcopy(change)
    response = client.post(PATH, json=request, headers=auth(ids))
    assert response.status_code == 422, response.text
    assert counts(factory) == before


@pytest.mark.parametrize("user,org,path,status", [
    ("viewer@example.com", "demo-org", PATH, 403),
    ("other@example.com", "northwind-org", PATH, 404),
    ("tech@example.com", "demo-org", PATH.replace("AC-07", "missing"), 404),
])
def test_batch_authorization(api, user, org, path, status):
    client, ids, factory = api
    before = counts(factory)
    response = client.post(path, json=payload(), headers=auth(ids, org=org, user=user))
    assert response.status_code == status
    assert counts(factory) == before


def test_batch_retry_in_equivalent_timezone_is_conflict(api):
    client, ids, factory = api
    assert client.post(PATH, json=payload(), headers=auth(ids)).status_code == 201
    before = counts(factory)
    request = payload() | {"recordedAt": "2026-11-11T06:30:00Z"}
    response = client.post(PATH, json=request, headers=auth(ids))
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CONFLICT"
    assert counts(factory) == before


def test_existing_item_rejects_entire_batch(api):
    client, ids, factory = api
    request = payload()
    existing = request["items"][1] | {
        "source": "manual", "recordedAt": request["recordedAt"]
    }
    assert client.post(PATH.removesuffix("/batch"), json=existing, headers=auth(ids)).status_code == 201
    before = counts(factory)
    response = client.post(PATH, json=request, headers=auth(ids))
    assert response.status_code == 409
    assert counts(factory) == before


def test_unique_constraint_rolls_back_earlier_items(api, monkeypatch):
    client, ids, factory = api
    request = payload()
    existing = request["items"][1] | {
        "source": "manual", "recordedAt": "2026-11-11T06:30:00Z"
    }
    assert client.post(PATH.removesuffix("/batch"), json=existing, headers=auth(ids)).status_code == 201
    before = counts(factory)
    # Simulate another writer winning after the preflight duplicate check.
    monkeypatch.setattr(device_parameters, "_duplicate_exists", lambda *a, **kw: False)
    response = client.post(PATH, json=request, headers=auth(ids))
    assert response.status_code == 409
    assert counts(factory) == before


def test_audit_failure_rolls_back_parameters_and_prior_audit(api, monkeypatch):
    client, ids, factory = api
    before = counts(factory)
    original = device_parameters.write_audit
    calls = []

    def failing_audit(*args, **kwargs):
        calls.append(kwargs)
        if len(calls) == 2:
            raise RuntimeError("simulated audit failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(device_parameters, "write_audit", failing_audit)
    with pytest.raises(RuntimeError, match="simulated audit failure"):
        client.post(PATH, json=payload(), headers=auth(ids))
    assert len(calls) == 2
    assert counts(factory) == before


def test_same_metrics_at_new_time_are_new_inspection(api):
    client, ids, factory = api
    assert client.post(PATH, json=payload(), headers=auth(ids)).status_code == 201
    before = counts(factory)
    request = payload() | {"recordedAt": "2026-11-11T14:31:00+08:00"}
    assert client.post(PATH, json=request, headers=auth(ids)).status_code == 201
    assert counts(factory) == (before[0] + 2, before[1] + 2)


def test_batch_requires_token_even_with_forged_identity_headers(api, monkeypatch):
    client, ids, factory = api
    before = counts(factory)
    monkeypatch.setattr(deps, "AUTH_MODE", "token")
    response = client.post(PATH, json=payload(), headers=auth(ids))
    assert response.status_code == 401
    assert counts(factory) == before


def test_batch_accepts_maximum_size_and_decimal_boundaries(api):
    client, ids, factory = api
    before = counts(factory)
    request = payload() | {"items": [
        {"name": f"metric_{i}", "value": "-999999999999.999999" if i == 0 else "0.000001"}
        for i in range(100)
    ]}
    response = client.post(PATH, json=request, headers=auth(ids))
    assert response.status_code == 201, response.text
    assert response.json()["total"] == 100
    assert counts(factory) == (before[0] + 100, before[1] + 100)

from sqlalchemy import select
from test_crud import auth

from app.models import AuditLog


def test_archive_preserves_original_and_is_idempotent(api):
    client, ids, factory = api
    headers = auth(ids)
    rows = client.get("/api/v1/audit-events", headers=headers).json()["items"]
    event_id = rows[0]["id"]
    url = f"/api/v1/audit-events/{event_id}"
    assert client.delete(url, headers=headers).status_code == 200
    assert client.delete(url, headers=headers).status_code == 200
    remaining = client.get("/api/v1/audit-events", headers=headers).json()["items"]
    assert event_id not in {row["id"] for row in remaining}
    assert len(remaining) == len(rows) - 1
    internal = client.get("/api/v1/audit-events?includeInternal=true", headers=headers).json()["items"]
    marker = next(row for row in internal if row["action"] == "audit.archive")
    assert client.delete(f"/api/v1/audit-events/{marker['id']}", headers=headers).status_code == 409
    import uuid
    with factory() as db:
        assert db.scalar(select(AuditLog).where(AuditLog.id == uuid.UUID(event_id))) is not None


def test_annotation_persists_without_replacing_original(api):
    client, ids, _ = api
    headers = auth(ids)
    original = client.get("/api/v1/audit-events", headers=headers).json()["items"][0]
    url = f"/api/v1/audit-events/{original['id']}"
    payload = {"ownerName": "张工", "note": "补充现场维修人员"}
    assert client.patch(url, headers=headers, json=payload).status_code == 200
    rows = client.get("/api/v1/audit-events", headers=headers).json()["items"]
    updated = next(row for row in rows if row["id"] == original["id"])
    assert updated["annotation"] == payload
    assert updated["after"] == original["after"]
    foreign = auth(ids, org="northwind-org", user="other@example.com")
    assert client.patch(url, headers=foreign, json=payload).status_code in (403, 404)
    assert client.delete(url, headers=foreign).status_code in (403, 404)
    assert client.delete(url, headers=headers).status_code == 200
    assert client.patch(url, headers=headers, json=payload).status_code == 409

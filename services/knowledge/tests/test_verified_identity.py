import httpx
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
ORG = "00000000-0000-4000-8000-000000000001"
USER = "00000000-0000-4000-8000-000000000101"


def _identity(role):
    return httpx.Response(200, json={
        "organization": {"id": ORG}, "user": {"id": USER}, "role": role,
    })


def test_verified_identity_rejects_missing_token_and_header_spoofing(monkeypatch):
    monkeypatch.setenv("C_IDENTITY_API_BASE_URL", "http://business.test")
    monkeypatch.setattr("app.api.context.httpx.get", lambda *args, **kwargs: _identity("manager"))
    assert client.get("/api/v1/documents", headers={"X-Organization-Id": ORG}).status_code == 401
    denied = client.get("/api/v1/documents", headers={
        "Authorization": "Bearer valid", "X-Organization-Id": "another-org",
    })
    assert denied.status_code == 403
    allowed = client.get("/api/v1/documents", headers={
        "Authorization": "Bearer valid", "X-Organization-Id": ORG,
    })
    assert allowed.status_code == 200


def test_document_upload_requires_manager_when_identity_is_verified(monkeypatch):
    monkeypatch.setenv("C_IDENTITY_API_BASE_URL", "http://business.test")
    role = {"value": "viewer"}
    monkeypatch.setattr("app.api.context.httpx.get", lambda *args, **kwargs: _identity(role["value"]))
    headers = {"Authorization": "Bearer valid", "X-Organization-Id": ORG}
    form = {"equipment_model": "AC-07", "title": "手册"}
    files = {"file": ("manual.txt", b"Check temperature against nameplate.", "text/plain")}
    denied = client.post("/api/v1/documents/upload", headers=headers, data=form, files=files)
    assert denied.status_code == 403
    role["value"] = "manager"
    allowed = client.post("/api/v1/documents/upload", headers=headers, data=form, files=files)
    assert allowed.status_code == 200
    assert allowed.json()["chunk_count"] == 1


def test_document_preview_delete_and_text_ingest_follow_verified_role(monkeypatch):
    monkeypatch.setenv("C_IDENTITY_API_BASE_URL", "http://business.test")
    role = {"value": "viewer"}
    monkeypatch.setattr("app.api.context.httpx.get", lambda *args, **kwargs: _identity(role["value"]))
    headers = {"Authorization": "Bearer valid", "X-Organization-Id": ORG}
    payload = {
        "title": "空压机规程", "equipment_model": "GX11",
        "content": "排气温度检查冷却器。", "source": "虚构手册",
    }
    assert client.post("/api/v1/documents/ingest", headers=headers, json=payload).status_code == 403

    role["value"] = "manager"
    created = client.post("/api/v1/documents/ingest", headers=headers, json=payload)
    assert created.status_code == 200
    document_id = created.json()["document_id"]
    role["value"] = "viewer"
    detail = client.get(f"/api/v1/documents/{document_id}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["document"]["title"] == "空压机规程"
    assert detail.json()["chunks"][0]["text"] == payload["content"]
    assert client.delete(f"/api/v1/documents/{document_id}", headers=headers).status_code == 403

    role["value"] = "manager"
    assert client.delete(f"/api/v1/documents/{document_id}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/documents/{document_id}", headers=headers).status_code == 404
    assert client.post("/api/v1/search", headers=headers, json={"query": "冷却器"}).json()["count"] == 0


def test_production_requires_identity_api_configuration(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("C_IDENTITY_API_BASE_URL", raising=False)
    response = client.get("/api/v1/documents", headers={"X-Organization-Id": ORG})
    assert response.status_code == 503

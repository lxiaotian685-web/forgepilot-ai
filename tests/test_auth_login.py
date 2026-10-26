from __future__ import annotations

from sqlalchemy import select

from app.models import AuditLog

DEMO_PASSWORD = "ForgePilot123!"
SECRET = "test-secret-value-32-characters-long"


def test_login_and_me(api, monkeypatch):
    client, ids, _ = api
    monkeypatch.setenv("AUTH_SECRET", SECRET)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tokenType"] == "Bearer"
    assert body["role"] == "owner"
    assert body["organization"]["code"] == "demo-org"

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['accessToken']}"},
    )
    assert me.status_code == 200
    assert me.json()["user"]["email"] == "demo@example.com"
    assert me.json()["role"] == "owner"


def test_login_wrong_password_and_unknown_user(api, monkeypatch):
    client, ids, _ = api
    monkeypatch.setenv("AUTH_SECRET", SECRET)
    wrong = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": "wrong-password"},
    )
    assert wrong.status_code == 401
    assert wrong.json()["error"]["message"] == "邮箱或密码错误"

    unknown = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "whatever"},
    )
    assert unknown.status_code == 401
    assert unknown.json()["error"]["message"] == "邮箱或密码错误"


def test_login_org_mismatch_and_single_org_resolution(api, monkeypatch):
    client, ids, _ = api
    monkeypatch.setenv("AUTH_SECRET", SECRET)
    mismatched = client.post(
        "/api/v1/auth/login",
        json={
            "email": "other@example.com",
            "password": DEMO_PASSWORD,
            "organizationCode": "demo-org",
        },
    )
    assert mismatched.status_code == 403

    resolved = client.post(
        "/api/v1/auth/login",
        json={
            "email": "other@example.com",
            "password": DEMO_PASSWORD,
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["organization"]["code"] == "northwind-org"


def test_login_token_identity_overrides_demo_headers(api, monkeypatch):
    client, ids, _ = api
    monkeypatch.setenv("AUTH_SECRET", SECRET)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": DEMO_PASSWORD},
    )
    token = login.json()["accessToken"]
    response = client.get(
        "/api/v1/devices",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Organization-Id": "demo-org",
            "X-User-Id": "demo@example.com",
        },
    )
    assert response.status_code == 200
    device_ids = {item["id"] for item in response.json()["items"]}
    assert "NV-01" in device_ids
    assert "AC-07" not in device_ids


def test_login_writes_audit(api, monkeypatch):
    client, ids, session_factory = api
    monkeypatch.setenv("AUTH_SECRET", SECRET)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 200
    with session_factory() as session:
        entry = session.scalar(
            select(AuditLog).where(AuditLog.action == "auth.login")
        )
        assert entry is not None


def test_login_requires_configured_secret(api, monkeypatch):
    client, ids, _ = api
    monkeypatch.delenv("AUTH_SECRET", raising=False)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "demo@example.com", "password": DEMO_PASSWORD},
    )
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "INTERNAL_ERROR"

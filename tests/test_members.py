from __future__ import annotations

from sqlalchemy import select

from app.models import AuditLog, Membership, WorkOrder


def auth(ids: dict, org: str = "demo-org", user: str = "demo@example.com") -> dict:
    return {
        "X-Organization-Id": str(ids["organizations"][org]),
        "X-User-Id": str(ids["users"][user]),
    }


def test_member_list_is_filtered_and_organization_scoped(api):
    client, ids, _ = api
    response = client.get(
        "/api/v1/members",
        params={"role": "technician", "q": "张"},
        headers=auth(ids, user="manager@example.com"),
    )
    assert response.status_code == 200
    assert [item["email"] for item in response.json()["items"]] == ["tech@example.com"]
    assert response.json()["items"][0]["openWorkOrderCount"] >= 0

    other = client.get(
        "/api/v1/members",
        headers=auth(ids, org="northwind-org", user="other@example.com"),
    )
    assert other.status_code == 200
    assert [item["email"] for item in other.json()["items"]] == ["other@example.com"]


def test_member_list_requires_manager(api):
    client, ids, _ = api
    response = client.get(
        "/api/v1/members", headers=auth(ids, user="tech@example.com")
    )
    assert response.status_code == 403


def test_owner_can_create_member_and_duplicate_is_rejected(api):
    client, ids, session_factory = api
    payload = {
        "email": "new.tech@example.com",
        "displayName": "新维修员",
        "role": "technician",
        "initialPassword": "SafePass123!",
    }
    created = client.post("/api/v1/members", json=payload, headers=auth(ids))
    assert created.status_code == 201
    assert created.json()["status"] == "active"
    assert created.json()["role"] == "technician"

    duplicate = client.post("/api/v1/members", json=payload, headers=auth(ids))
    assert duplicate.status_code == 409

    with session_factory() as session:
        entry = session.scalar(select(AuditLog).where(AuditLog.action == "member.create"))
        assert entry is not None


def test_admin_cannot_manage_owner_or_grant_admin(api):
    client, ids, session_factory = api
    with session_factory() as session:
        manager = session.scalar(
            select(Membership).where(
                Membership.user_id == ids["users"]["manager@example.com"],
                Membership.organization_id == ids["organizations"]["demo-org"],
            )
        )
        manager.role = "admin"
        session.commit()

    grant = client.patch(
        f'/api/v1/members/{ids["users"]["tech@example.com"]}',
        json={"role": "admin"},
        headers=auth(ids, user="manager@example.com"),
    )
    assert grant.status_code == 403

    owner = client.patch(
        f'/api/v1/members/{ids["users"]["demo@example.com"]}',
        json={"displayName": "不可修改"},
        headers=auth(ids, user="manager@example.com"),
    )
    assert owner.status_code == 403


def test_disable_requires_reassignment_and_moves_open_orders(api):
    client, ids, session_factory = api
    tech_id = ids["users"]["tech@example.com"]
    recipient_id = ids["users"]["zhao@example.com"]

    blocked = client.patch(
        f"/api/v1/members/{tech_id}",
        json={"status": "disabled"},
        headers=auth(ids),
    )
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "OPEN_WORK_ORDERS"
    assert blocked.json()["error"]["details"]["count"] > 0

    updated = client.patch(
        f"/api/v1/members/{tech_id}",
        json={"status": "disabled", "reassignToUserId": str(recipient_id)},
        headers=auth(ids),
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "disabled"
    assert updated.json()["openWorkOrderCount"] == 0

    with session_factory() as session:
        active_orders = session.scalars(
            select(WorkOrder).where(
                WorkOrder.organization_id == ids["organizations"]["demo-org"],
                WorkOrder.status.in_({"pending", "processing", "verifying"}),
            )
        ).all()
        assert all(order.owner_user_id != tech_id for order in active_orders)
        assert any(order.owner_user_id == recipient_id for order in active_orders)
        audit = session.scalar(select(AuditLog).where(AuditLog.action == "member.update"))
        assert audit is not None
        assert audit.after["reassignedToUserId"] == str(recipient_id)
        assert audit.after["reassignedOpenWorkOrderCount"] > 0
        assert audit.after["reassignedWorkOrderIds"]


def test_disable_rejects_viewer_recipient(api):
    client, ids, _ = api
    response = client.patch(
        f'/api/v1/members/{ids["users"]["tech@example.com"]}',
        json={
            "status": "disabled",
            "reassignToUserId": str(ids["users"]["viewer@example.com"]),
        },
        headers=auth(ids),
    )
    assert response.status_code == 422
    assert "维修人员权限" in response.json()["error"]["message"]


def test_last_owner_cannot_be_demoted(api):
    client, ids, _ = api
    response = client.patch(
        f'/api/v1/members/{ids["users"]["demo@example.com"]}',
        json={"role": "manager"},
        headers=auth(ids),
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "LAST_OWNER"


def test_reassignment_is_only_valid_during_disable(api):
    client, ids, _ = api
    response = client.patch(
        f'/api/v1/members/{ids["users"]["tech@example.com"]}',
        json={
            "displayName": "张师傅",
            "reassignToUserId": str(ids["users"]["zhao@example.com"]),
        },
        headers=auth(ids),
    )
    assert response.status_code == 422


def test_member_update_rejects_cross_org_and_self_disable(api):
    client, ids, _ = api
    cross_org = client.patch(
        f'/api/v1/members/{ids["users"]["other@example.com"]}',
        json={"role": "viewer"},
        headers=auth(ids),
    )
    assert cross_org.status_code == 404

    self_disable = client.patch(
        f'/api/v1/members/{ids["users"]["demo@example.com"]}',
        json={"status": "disabled"},
        headers=auth(ids),
    )
    assert self_disable.status_code == 409
    assert self_disable.json()["error"]["code"] == "SELF_DISABLE"

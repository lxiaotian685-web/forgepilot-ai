from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.auth import verify_token
from app.db import get_db
from app.models import Membership, Organization, User

DEMO_ORG_CODE = "demo-org"
DEMO_USER_EMAIL = "demo@example.com"
AUTH_MODE = os.getenv("AUTH_MODE", "demo")

ROLE_LEVELS = {
    "viewer": 0,
    "technician": 1,
    "manager": 2,
    "admin": 3,
    "owner": 4,
}


@dataclass(frozen=True)
class RequestContext:
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: str


def _parse_uuid(value: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(value)
    except ValueError:
        return None


def _resolve_organization(db: Session, value: str | None) -> Organization:
    if value:
        parsed = _parse_uuid(value)
        org = (
            db.get(Organization, parsed)
            if parsed
            else db.scalar(select(Organization).where(Organization.code == value))
        )
    else:
        org = db.scalar(
            select(Organization).where(Organization.code == DEMO_ORG_CODE)
        )
    if org is None or org.status != "active":
        raise api_error(401, "UNAUTHORIZED", "组织不存在或已停用")
    return org


def _resolve_user(db: Session, value: str | None) -> User:
    if value:
        parsed = _parse_uuid(value)
        user = (
            db.get(User, parsed)
            if parsed
            else db.scalar(select(User).where(User.email == value))
        )
    else:
        user = db.scalar(select(User).where(User.email == DEMO_USER_EMAIL))
    if user is None or user.status != "active":
        raise api_error(401, "UNAUTHORIZED", "用户不存在或已停用")
    return user


def _identity_from_token(authorization: str | None) -> tuple[str, str]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise api_error(401, "UNAUTHORIZED", "缺少 Bearer 令牌")
    token = authorization.split(" ", 1)[1].strip()
    payload = verify_token(token)
    if payload is None:
        raise api_error(401, "UNAUTHORIZED", "令牌无效或已过期")
    return payload["org"], payload["user"]


def get_context(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_organization_id: str | None = Header(default=None, alias="X-Organization-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
) -> RequestContext:
    if authorization and authorization.lower().startswith("bearer "):
        org_value, user_value = _identity_from_token(authorization)
    elif AUTH_MODE == "token":
        raise api_error(401, "UNAUTHORIZED", "缺少 Bearer 令牌")
    else:
        org_value, user_value = x_organization_id, x_user_id
    org = _resolve_organization(db, org_value)
    user = _resolve_user(db, user_value)
    membership = db.scalar(
        select(Membership).where(
            Membership.organization_id == org.id,
            Membership.user_id == user.id,
            Membership.status == "active",
        )
    )
    if membership is None:
        raise api_error(403, "FORBIDDEN", "当前用户不属于该组织")
    return RequestContext(
        organization_id=org.id, user_id=user.id, role=membership.role
    )


def require_role(context: RequestContext, minimum: str) -> None:
    if ROLE_LEVELS.get(context.role, -1) < ROLE_LEVELS[minimum]:
        raise api_error(
            403,
            "FORBIDDEN",
            "当前角色无权执行该操作",
            {"requiredRole": minimum, "role": context.role},
        )

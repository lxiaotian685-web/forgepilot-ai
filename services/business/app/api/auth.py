from __future__ import annotations

import os

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.audit import write_audit
from app.api.deps import RequestContext, get_context
from app.api.errors import api_error
from app.auth import issue_token
from app.db import get_db
from app.models import Membership, Organization, User
from app.schemas.requests import LoginRequest
from app.security import verify_password

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _token_ttl() -> int:
    try:
        ttl = int(os.getenv("AUTH_TOKEN_TTL_SECONDS", "3600"))
    except ValueError:
        return 3600
    return ttl if ttl > 0 else 3600


def _organization_for_user(
    db: Session, user: User, organization_code: str | None
):
    if organization_code:
        organization = db.scalar(
            select(Organization).where(
                Organization.code == organization_code,
                Organization.status == "active",
            )
        )
        if organization is None:
            return None, None
        membership = db.scalar(
            select(Membership).where(
                Membership.organization_id == organization.id,
                Membership.user_id == user.id,
                Membership.status == "active",
            )
        )
        return organization, membership

    memberships = db.scalars(
        select(Membership).where(
            Membership.user_id == user.id,
            Membership.status == "active",
        )
    ).all()
    if len(memberships) != 1:
        return None, None
    membership = memberships[0]
    organization = db.get(Organization, membership.organization_id)
    if organization is None or organization.status != "active":
        return None, None
    return organization, membership


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == payload.email))
    if (
        user is None
        or user.status != "active"
        or not verify_password(payload.password, user.password_hash)
    ):
        raise api_error(401, "UNAUTHORIZED", "邮箱或密码错误")

    organization, membership = _organization_for_user(
        db, user, payload.organization_code
    )
    if organization is None or membership is None:
        raise api_error(403, "FORBIDDEN", "用户不属于该组织或已停用")

    ttl = _token_ttl()
    try:
        token = issue_token(
            organization.code, user.email, ttl_seconds=ttl
        )
    except RuntimeError:
        raise api_error(
            500, "INTERNAL_ERROR", "认证服务未配置 AUTH_SECRET"
        )

    write_audit(
        db,
        organization_id=organization.id,
        actor_user_id=user.id,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        after={
            "email": user.email,
            "organization": organization.code,
        },
    )
    db.commit()
    return {
        "accessToken": token,
        "tokenType": "Bearer",
        "expiresIn": ttl,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "displayName": user.display_name,
        },
        "organization": {
            "id": str(organization.id),
            "code": organization.code,
            "name": organization.name,
        },
        "role": membership.role,
    }


@router.get("/me")
def me(
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    user = db.get(User, context.user_id)
    organization = db.get(Organization, context.organization_id)
    if user is None or organization is None:
        raise api_error(404, "NOT_FOUND", "用户或组织不存在")
    membership = db.scalar(
        select(Membership).where(
            Membership.organization_id == context.organization_id,
            Membership.user_id == context.user_id,
        )
    )
    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "displayName": user.display_name,
        },
        "organization": {
            "id": str(organization.id),
            "code": organization.code,
            "name": organization.name,
        },
        "role": membership.role if membership else context.role,
    }

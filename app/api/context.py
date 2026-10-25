from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

from app.config import auth_required, default_organization_id


@dataclass(frozen=True)
class RequestContext:
    organization_id: str
    user_id: str | None = None
    token: str | None = None


def get_request_context(
    x_organization_id: str | None = Header(
        default=None, alias="X-Organization-Id"
    ),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> RequestContext:
    token = None
    if authorization and authorization[:7].lower() == "bearer ":
        token = authorization[7:].strip() or None

    organization_id = x_organization_id.strip() if x_organization_id else ""
    if not organization_id:
        if auth_required():
            raise HTTPException(
                status_code=401,
                detail="缺少组织上下文（X-Organization-Id），请通过网关或登录态注入",
            )
        organization_id = default_organization_id()

    if len(organization_id) > 100:
        raise HTTPException(status_code=422, detail="组织编号过长")

    return RequestContext(
        organization_id=organization_id,
        user_id=x_user_id.strip() if x_user_id else None,
        token=token,
    )

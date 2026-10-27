from __future__ import annotations

from dataclasses import dataclass

import httpx
from fastapi import Header, HTTPException

from app.config import (
    auth_required,
    default_organization_id,
    identity_api_base_url,
    is_production,
)


@dataclass(frozen=True)
class RequestContext:
    organization_id: str
    user_id: str | None = None
    token: str | None = None
    role: str | None = None


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

    identity_base = identity_api_base_url()
    if is_production() and not identity_base:
        raise HTTPException(status_code=503, detail="身份校验服务未配置")
    if identity_base:
        if not token:
            raise HTTPException(status_code=401, detail="缺少 Bearer 令牌")
        try:
            response = httpx.get(
                f"{identity_base}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {token}"},
                timeout=5.0,
                trust_env=False,
            )
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=503, detail="身份校验服务不可用") from exc
        if response.status_code in {401, 403}:
            raise HTTPException(status_code=401, detail="登录身份无效或已停用")
        if response.status_code != 200:
            raise HTTPException(status_code=503, detail="身份校验服务返回异常")
        try:
            identity = response.json()
            verified_org = identity["organization"]["id"]
            verified_user = identity["user"]["id"]
            verified_role = identity["role"]
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(status_code=503, detail="身份校验响应格式不正确") from exc
        if not all(isinstance(value, str) and value for value in (verified_org, verified_user, verified_role)):
            raise HTTPException(status_code=503, detail="身份校验响应缺少身份字段")
        if x_organization_id and x_organization_id.strip() != verified_org:
            raise HTTPException(status_code=403, detail="请求组织与登录组织不一致")
        if x_user_id and x_user_id.strip() != verified_user:
            raise HTTPException(status_code=403, detail="请求人员与登录人员不一致")
        return RequestContext(
            organization_id=verified_org,
            user_id=verified_user,
            token=token,
            role=verified_role,
        )

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

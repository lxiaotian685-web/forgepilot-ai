from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.audit import write_audit
from app.api.deps import ROLE_LEVELS, RequestContext, get_context, require_role
from app.api.errors import api_error
from app.api.serializers import member_to_dict, page_response
from app.db import get_db
from app.models import Membership, User, WorkOrder
from app.schemas.requests import MemberCreate, MemberUpdate
from app.security import hash_password

router = APIRouter(prefix="/api/v1/members", tags=["members"])

ROLES = set(ROLE_LEVELS)
STATUSES = {"active", "disabled"}
OPEN_ORDER_STATUSES = {"pending", "processing", "verifying"}


def _validate_role(role: str) -> None:
    if role not in ROLES:
        raise api_error(422, "VALIDATION_ERROR", "角色不合法", {"role": role})


def _member(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID):
    row = db.execute(
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
        )
    ).first()
    if row is None:
        raise api_error(404, "NOT_FOUND", "成员不存在")
    return row


def _assert_can_manage(context: RequestContext, target_role: str) -> None:
    if context.role != "owner" and target_role in {"owner", "admin"}:
        raise api_error(403, "FORBIDDEN", "只有组织所有者可以管理所有者或管理员")


def _open_order_count(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID) -> int:
    return db.scalar(
        select(func.count()).select_from(WorkOrder).where(
            WorkOrder.organization_id == organization_id,
            WorkOrder.owner_user_id == user_id,
            WorkOrder.status.in_(OPEN_ORDER_STATUSES),
            WorkOrder.deleted_at.is_(None),
        )
    ) or 0


def _lock_active_owners(db: Session, organization_id: uuid.UUID) -> list[Membership]:
    return db.scalars(
        select(Membership)
        .where(
            Membership.organization_id == organization_id,
            Membership.role == "owner",
            Membership.status == "active",
        )
        .with_for_update()
    ).all()


@router.get("")
def list_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    q: str | None = Query(default=None),
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "manager")
    if role:
        _validate_role(role)
    if status and status not in STATUSES:
        raise api_error(422, "VALIDATION_ERROR", "成员状态不合法", {"status": status})
    stmt = (
        select(Membership, User)
        .join(User, User.id == Membership.user_id)
        .where(Membership.organization_id == context.organization_id)
    )
    if role:
        stmt = stmt.where(Membership.role == role)
    if status:
        stmt = stmt.where(Membership.status == status)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.display_name.ilike(like), User.email.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.execute(
        stmt.order_by(User.display_name).offset((page - 1) * page_size).limit(page_size)
    ).all()
    user_ids = [user.id for _, user in rows]
    counts = dict(
        db.execute(
            select(WorkOrder.owner_user_id, func.count())
            .where(
                WorkOrder.organization_id == context.organization_id,
                WorkOrder.owner_user_id.in_(user_ids),
                WorkOrder.status.in_(OPEN_ORDER_STATUSES),
                WorkOrder.deleted_at.is_(None),
            )
            .group_by(WorkOrder.owner_user_id)
        ).all()
    ) if user_ids else {}
    return page_response(
        [member_to_dict(membership, user, counts.get(user.id, 0)) for membership, user in rows],
        page,
        page_size,
        total,
    )


@router.post("", status_code=201)
def create_member(
    payload: MemberCreate,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "admin")
    _validate_role(payload.role)
    _assert_can_manage(context, payload.role)
    email = payload.email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if user is None:
        if not payload.initial_password:
            raise api_error(422, "VALIDATION_ERROR", "新用户必须设置初始密码")
        user = User(
            email=email,
            display_name=payload.display_name.strip(),
            password_hash=hash_password(payload.initial_password),
            status="active",
        )
        db.add(user)
        db.flush()
    else:
        if user.status != "active":
            raise api_error(409, "CONFLICT", "该用户账号已停用，不能加入组织")
        if db.scalar(select(Membership).where(
            Membership.organization_id == context.organization_id,
            Membership.user_id == user.id,
        )):
            raise api_error(409, "CONFLICT", "该用户已是组织成员")

    membership = Membership(
        organization_id=context.organization_id,
        user_id=user.id,
        role=payload.role,
        status="active",
    )
    db.add(membership)
    db.flush()
    write_audit(
        db,
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        action="member.create",
        entity_type="membership",
        entity_id=membership.id,
        after={"userId": str(user.id), "email": user.email, "role": membership.role},
    )
    db.commit()
    db.refresh(membership)
    return member_to_dict(membership, user)


@router.patch("/{user_id}")
def update_member(
    user_id: uuid.UUID,
    payload: MemberUpdate,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "admin")
    membership, user = _member(db, context.organization_id, user_id)
    _assert_can_manage(context, membership.role)
    fields = payload.model_fields_set
    before = {"displayName": user.display_name, "role": membership.role, "status": membership.status}
    reassignment = None

    if "reassign_to_user_id" in fields and not (
        payload.status == "disabled" and membership.status != "disabled"
    ):
        raise api_error(422, "VALIDATION_ERROR", "转派人员只能在停用成员时指定")

    if "role" in fields and payload.role is not None:
        _validate_role(payload.role)
        _assert_can_manage(context, payload.role)
        if membership.role == "owner" and payload.role != "owner":
            if len(_lock_active_owners(db, context.organization_id)) <= 1:
                raise api_error(409, "LAST_OWNER", "组织必须保留至少一名启用的所有者")
        membership.role = payload.role

    if "status" in fields and payload.status is not None:
        if payload.status not in STATUSES:
            raise api_error(422, "VALIDATION_ERROR", "成员状态不合法", {"status": payload.status})
        if payload.status == "disabled" and membership.status != "disabled":
            if user.id == context.user_id:
                raise api_error(409, "SELF_DISABLE", "不能停用当前登录成员")
            if membership.role == "owner":
                if len(_lock_active_owners(db, context.organization_id)) <= 1:
                    raise api_error(409, "LAST_OWNER", "组织必须保留至少一名启用的所有者")
            open_count = _open_order_count(db, context.organization_id, user.id)
            if open_count:
                if payload.reassign_to_user_id is None:
                    raise api_error(409, "OPEN_WORK_ORDERS", "成员仍有未完成工单，请先选择转派人员", {"count": open_count})
                if payload.reassign_to_user_id == user.id:
                    raise api_error(422, "VALIDATION_ERROR", "转派人员不能是被停用成员")
                recipient_membership, recipient = _member(db, context.organization_id, payload.reassign_to_user_id)
                if recipient_membership.status != "active" or recipient.status != "active":
                    raise api_error(422, "VALIDATION_ERROR", "转派人员必须是当前组织的启用成员")
                if ROLE_LEVELS.get(recipient_membership.role, -1) < ROLE_LEVELS["technician"]:
                    raise api_error(422, "VALIDATION_ERROR", "转派人员至少需要维修人员权限")
                open_orders = db.scalars(
                    select(WorkOrder).where(
                        WorkOrder.organization_id == context.organization_id,
                        WorkOrder.owner_user_id == user.id,
                        WorkOrder.status.in_(OPEN_ORDER_STATUSES),
                        WorkOrder.deleted_at.is_(None),
                    ).with_for_update()
                ).all()
                for order in open_orders:
                    order.owner_user_id = recipient.id
                    order.updated_by = context.user_id
                reassignment = {
                    "reassignedToUserId": str(recipient.id),
                    "reassignedOpenWorkOrderCount": len(open_orders),
                    "reassignedWorkOrderIds": [order.code for order in open_orders],
                }
            membership.status = "disabled"
        elif payload.status == "active":
            if user.status != "active":
                raise api_error(409, "CONFLICT", "用户账号已停用，不能恢复组织成员")
            membership.status = "active"

    if "display_name" in fields and payload.display_name is not None:
        user.display_name = payload.display_name.strip()

    after = {"displayName": user.display_name, "role": membership.role, "status": membership.status}
    if reassignment:
        after.update(reassignment)
    write_audit(
        db,
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        action="member.update",
        entity_type="membership",
        entity_id=membership.id,
        before=before,
        after=after,
    )
    db.commit()
    return member_to_dict(membership, user, _open_order_count(db, context.organization_id, user.id))

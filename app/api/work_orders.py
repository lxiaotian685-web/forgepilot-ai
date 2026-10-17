from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.audit import write_audit
from app.api.deps import RequestContext, get_context, require_role
from app.api.errors import api_error
from app.api.labels import (
    WORK_ORDER_PRIORITY_LABELS,
    WORK_ORDER_STATUS_LABELS,
    WORK_ORDER_TRANSITIONS,
    label_to_code,
)
from app.api.serializers import page_response, work_order_to_dict
from app.db import get_db
from app.models import Alert, Device, Diagnosis, Membership, User, WorkOrder, utcnow
from app.schemas.requests import WorkOrderCreate, WorkOrderUpdate

router = APIRouter(prefix="/api/v1/work-orders", tags=["work-orders"])


def _get_device(
    db: Session, organization_id: uuid.UUID, code: str
) -> Device | None:
    return db.scalar(
        select(Device).where(
            Device.organization_id == organization_id,
            Device.code == code,
            Device.deleted_at.is_(None),
        )
    )


def _validate_owner(
    db: Session, organization_id: uuid.UUID, user_id: uuid.UUID
) -> User:
    membership = db.scalar(
        select(Membership).where(
            Membership.organization_id == organization_id,
            Membership.user_id == user_id,
            Membership.status == "active",
        )
    )
    user = db.get(User, user_id)
    if membership is None or user is None:
        raise api_error(
            422,
            "VALIDATION_ERROR",
            "负责人不属于当前组织",
            {"ownerId": str(user_id)},
        )
    return user


def _get_alert(
    db: Session, organization_id: uuid.UUID, code: str
) -> Alert:
    alert = db.scalar(
        select(Alert).where(
            Alert.organization_id == organization_id,
            Alert.code == code,
            Alert.deleted_at.is_(None),
        )
    )
    if alert is None:
        raise api_error(
            422, "VALIDATION_ERROR", "来源告警不存在", {"alertId": code}
        )
    return alert


def _get_diagnosis(
    db: Session, organization_id: uuid.UUID, code: str
) -> Diagnosis:
    diagnosis = db.scalar(
        select(Diagnosis).where(
            Diagnosis.organization_id == organization_id,
            Diagnosis.code == code,
            Diagnosis.deleted_at.is_(None),
        )
    )
    if diagnosis is None:
        raise api_error(
            422, "VALIDATION_ERROR", "来源诊断不存在", {"diagnosisId": code}
        )
    return diagnosis


def _next_code(
    db: Session, organization_id: uuid.UUID, now: datetime
) -> str:
    prefix = f"WO-{now:%Y%m%d}-"
    existing = db.scalar(
        select(func.count())
        .select_from(WorkOrder)
        .where(
            WorkOrder.organization_id == organization_id,
            WorkOrder.code.like(f"{prefix}%"),
        )
    ) or 0
    sequence = existing + 1
    for _ in range(100):
        code = f"{prefix}{sequence:02d}"
        found = db.scalar(
            select(WorkOrder.id).where(
                WorkOrder.organization_id == organization_id,
                WorkOrder.code == code,
            )
        )
        if found is None:
            return code
        sequence += 1
    raise api_error(409, "CONFLICT", "无法生成唯一工单号")


def _load_related(db: Session, orders: list[WorkOrder]):
    device_ids = {order.device_id for order in orders}
    owner_ids = {
        order.owner_user_id for order in orders if order.owner_user_id
    }
    devices = (
        {
            device.id: device
            for device in db.scalars(
                select(Device).where(Device.id.in_(device_ids))
            ).all()
        }
        if device_ids
        else {}
    )
    owners = (
        {
            user.id: user
            for user in db.scalars(
                select(User).where(User.id.in_(owner_ids))
            ).all()
        }
        if owner_ids
        else {}
    )
    return devices, owners


@router.get("")
def list_work_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    owner_id: uuid.UUID | None = Query(default=None, alias="ownerId"),
    device_id: str | None = Query(default=None, alias="deviceId"),
    q: str | None = Query(default=None),
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    stmt = select(WorkOrder).where(
        WorkOrder.organization_id == context.organization_id,
        WorkOrder.deleted_at.is_(None),
    )
    if status:
        stmt = stmt.where(
            WorkOrder.status
            == label_to_code(status, WORK_ORDER_STATUS_LABELS, "status")
        )
    if priority:
        stmt = stmt.where(
            WorkOrder.priority
            == label_to_code(priority, WORK_ORDER_PRIORITY_LABELS, "priority")
        )
    if owner_id:
        stmt = stmt.where(WorkOrder.owner_user_id == owner_id)
    if device_id:
        stmt = stmt.join(Device, WorkOrder.device_id == Device.id).where(
            Device.organization_id == context.organization_id,
            Device.code == device_id,
            Device.deleted_at.is_(None),
        )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(WorkOrder.code.ilike(like), WorkOrder.title.ilike(like))
        )

    stmt = stmt.order_by(WorkOrder.updated_at.desc())
    total = (
        db.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        or 0
    )
    orders = db.scalars(
        stmt.offset((page - 1) * page_size).limit(page_size)
    ).all()
    devices, owners = _load_related(db, orders)
    items = [
        work_order_to_dict(
            order,
            devices.get(order.device_id),
            owners.get(order.owner_user_id) if order.owner_user_id else None,
        )
        for order in orders
    ]
    return page_response(items, page, page_size, total)


@router.post("", status_code=201)
def create_work_order(
    payload: WorkOrderCreate,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "manager")
    device = _get_device(db, context.organization_id, payload.device_id)
    if device is None:
        raise api_error(404, "NOT_FOUND", "设备不存在")

    priority = label_to_code(
        payload.priority or "P3 中", WORK_ORDER_PRIORITY_LABELS, "priority"
    )
    owner = (
        _validate_owner(db, context.organization_id, payload.owner_id)
        if payload.owner_id
        else None
    )
    alert = (
        _get_alert(db, context.organization_id, payload.alert_id)
        if payload.alert_id
        else None
    )
    diagnosis = (
        _get_diagnosis(db, context.organization_id, payload.diagnosis_id)
        if payload.diagnosis_id
        else None
    )

    now = utcnow()
    order = WorkOrder(
        organization_id=context.organization_id,
        device_id=device.id,
        alert_id=alert.id if alert else None,
        diagnosis_id=diagnosis.id if diagnosis else None,
        code=_next_code(db, context.organization_id, now),
        title=payload.title,
        description=payload.description,
        priority=priority,
        status="pending",
        owner_user_id=owner.id if owner else None,
        due_at=payload.due_at,
        created_by=context.user_id,
        updated_by=context.user_id,
    )
    db.add(order)
    db.flush()
    write_audit(
        db,
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        action="work_order.create",
        entity_type="work_order",
        entity_id=order.id,
        after={
            "code": order.code,
            "status": order.status,
            "priority": order.priority,
            "deviceId": device.code,
        },
    )
    db.commit()
    db.refresh(order)
    return work_order_to_dict(order, device, owner)


@router.patch("/{work_order_id}")
def update_work_order(
    work_order_id: str,
    payload: WorkOrderUpdate,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "technician")
    order = db.scalar(
        select(WorkOrder).where(
            WorkOrder.organization_id == context.organization_id,
            WorkOrder.code == work_order_id,
            WorkOrder.deleted_at.is_(None),
        )
    )
    if order is None:
        raise api_error(404, "NOT_FOUND", "工单不存在")

    before = {
        "status": order.status,
        "priority": order.priority,
        "ownerId": str(order.owner_user_id) if order.owner_user_id else None,
    }
    fields = payload.model_fields_set

    if "status" in fields and payload.status:
        new_status = label_to_code(
            payload.status, WORK_ORDER_STATUS_LABELS, "status"
        )
        if new_status != order.status:
            allowed = WORK_ORDER_TRANSITIONS.get(order.status, set())
            if new_status not in allowed:
                raise api_error(
                    409,
                    "INVALID_TRANSITION",
                    (
                        "工单状态不能从 "
                        f"{WORK_ORDER_STATUS_LABELS.get(order.status, order.status)}"
                        " 流转到 "
                        f"{WORK_ORDER_STATUS_LABELS.get(new_status, new_status)}"
                    ),
                    {
                        "from": WORK_ORDER_STATUS_LABELS.get(
                            order.status, order.status
                        ),
                        "to": WORK_ORDER_STATUS_LABELS.get(
                            new_status, new_status
                        ),
                    },
                )
            order.status = new_status
            if new_status == "processing":
                order.closed_at = None
                if order.started_at is None:
                    order.started_at = utcnow()
            elif new_status == "completed":
                order.closed_at = utcnow()

    if "owner_id" in fields:
        if payload.owner_id is None:
            order.owner_user_id = None
        else:
            owner = _validate_owner(
                db, context.organization_id, payload.owner_id
            )
            order.owner_user_id = owner.id

    if "priority" in fields and payload.priority:
        order.priority = label_to_code(
            payload.priority, WORK_ORDER_PRIORITY_LABELS, "priority"
        )
    if "title" in fields and payload.title is not None:
        order.title = payload.title
    if "description" in fields:
        order.description = payload.description
    if "due_at" in fields:
        order.due_at = payload.due_at

    order.updated_by = context.user_id
    write_audit(
        db,
        organization_id=context.organization_id,
        actor_user_id=context.user_id,
        action="work_order.update",
        entity_type="work_order",
        entity_id=order.id,
        before=before,
        after={
            "status": order.status,
            "priority": order.priority,
            "ownerId": str(order.owner_user_id) if order.owner_user_id else None,
        },
    )
    db.commit()
    db.refresh(order)

    device = db.get(Device, order.device_id)
    owner = db.get(User, order.owner_user_id) if order.owner_user_id else None
    return work_order_to_dict(order, device, owner)

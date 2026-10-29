from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.audit import write_audit
from app.api.codes import next_work_order_code
from app.api.deps import ROLE_LEVELS, RequestContext, get_context, require_role
from app.api.errors import api_error
from app.api.labels import (
    WORK_ORDER_PRIORITY_LABELS,
    WORK_ORDER_STATUS_LABELS,
    WORK_ORDER_TRANSITIONS,
    label_to_code,
)
from app.api.serializers import page_response, work_order_to_dict
from app.db import get_db
from app.models import (
    Alert,
    Device,
    Diagnosis,
    MaintenanceRecord,
    Membership,
    User,
    WorkOrder,
    utcnow,
)
from app.schemas.requests import WorkOrderCreate, WorkOrderUpdate

router = APIRouter(prefix="/api/v1/work-orders", tags=["work-orders"])


def _validate_schedule(start, end) -> None:
    if start is not None and end is None:
        raise api_error(422, "VALIDATION_ERROR", "计划开始时间需要配套结束时间")
    if start is not None and end is not None and start.date() > end.date():
        raise api_error(422, "VALIDATION_ERROR", "计划结束日期不能早于开始日期")


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
    if membership is None or user is None or user.status != "active":
        raise api_error(
            422,
            "VALIDATION_ERROR",
            "负责人不存在、已停用或不属于当前组织",
            {"ownerId": str(user_id)},
        )
    if ROLE_LEVELS.get(membership.role, -1) < ROLE_LEVELS["technician"]:
        raise api_error(
            422,
            "VALIDATION_ERROR",
            "工单负责人至少需要维修人员权限",
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


def _load_related(db: Session, organization_id, orders: list[WorkOrder]):
    device_ids = {order.device_id for order in orders}
    owner_ids = {
        order.owner_user_id for order in orders if order.owner_user_id
    }
    alert_ids = {order.alert_id for order in orders if order.alert_id}
    diagnosis_ids = {
        order.diagnosis_id for order in orders if order.diagnosis_id
    }
    devices = (
        {
            device.id: device
            for device in db.scalars(
                select(Device).where(
                    Device.id.in_(device_ids),
                    Device.organization_id == organization_id,
                )
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
    alerts = (
        {
            alert.id: alert
            for alert in db.scalars(
                select(Alert).where(
                    Alert.id.in_(alert_ids),
                    Alert.organization_id == organization_id,
                )
            ).all()
        }
        if alert_ids
        else {}
    )
    diagnoses = (
        {
            diagnosis.id: diagnosis
            for diagnosis in db.scalars(
                select(Diagnosis).where(
                    Diagnosis.id.in_(diagnosis_ids),
                    Diagnosis.organization_id == organization_id,
                )
            ).all()
        }
        if diagnosis_ids
        else {}
    )
    return devices, owners, alerts, diagnoses


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
    devices, owners, alerts, diagnoses = _load_related(
        db, context.organization_id, orders
    )
    items = [
        work_order_to_dict(
            order,
            devices.get(order.device_id),
            owners.get(order.owner_user_id) if order.owner_user_id else None,
            alerts.get(order.alert_id) if order.alert_id else None,
            diagnoses.get(order.diagnosis_id)
            if order.diagnosis_id
            else None,
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
    if alert is not None and alert.device_id != device.id:
        raise api_error(
            422,
            "VALIDATION_ERROR",
            "来源告警不属于目标设备",
            {"alertId": alert.code, "deviceId": device.code},
        )
    if diagnosis is not None and diagnosis.device_id != device.id:
        raise api_error(
            422,
            "VALIDATION_ERROR",
            "来源诊断不属于目标设备",
            {"diagnosisId": diagnosis.code, "deviceId": device.code},
        )
    if diagnosis is not None:
        if diagnosis.status != "confirmed":
            raise api_error(
                409,
                "INVALID_STATE",
                "诊断尚未确认，不能创建工单",
                {"diagnosisId": diagnosis.code, "status": diagnosis.status},
            )
        existing_order = db.scalar(
            select(WorkOrder).where(
                WorkOrder.organization_id == context.organization_id,
                WorkOrder.diagnosis_id == diagnosis.id,
                WorkOrder.deleted_at.is_(None),
            )
        )
        if existing_order is not None:
            raise api_error(
                409,
                "CONFLICT",
                "该诊断已生成工单",
                {
                    "diagnosisId": diagnosis.code,
                    "workOrderId": existing_order.code,
                },
            )

    _validate_schedule(payload.planned_start_at, payload.due_at)
    now = utcnow()
    order = WorkOrder(
        organization_id=context.organization_id,
        device_id=device.id,
        alert_id=alert.id if alert else None,
        diagnosis_id=diagnosis.id if diagnosis else None,
        code=next_work_order_code(db, context.organization_id, now),
        title=payload.title,
        description=payload.description,
        priority=priority,
        status="pending",
        owner_user_id=owner.id if owner else None,
        planned_start_at=payload.planned_start_at,
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
            "plannedStartAt": order.planned_start_at.isoformat() if order.planned_start_at else None,
            "dueAt": order.due_at.isoformat() if order.due_at else None,
        },
    )
    db.commit()
    db.refresh(order)
    return work_order_to_dict(order, device, owner, alert, diagnosis)


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
        "plannedStartAt": order.planned_start_at.isoformat() if order.planned_start_at else None,
        "dueAt": order.due_at.isoformat() if order.due_at else None,
    }
    fields = payload.model_fields_set
    is_manager = ROLE_LEVELS.get(context.role, -1) >= ROLE_LEVELS["manager"]
    if not is_manager:
        if fields - {"status"}:
            raise api_error(403, "FORBIDDEN", "维修人员只能更新本人工单的执行状态")
        if order.owner_user_id != context.user_id:
            raise api_error(403, "FORBIDDEN", "只能处理指派给自己的工单")
        if payload.status in {"已完成", "已取消", "completed", "cancelled"}:
            raise api_error(403, "FORBIDDEN", "验收和取消工单需要主管权限")
    if payload.status in {"已取消", "cancelled"} and not payload.cancel_reason:
        raise api_error(422, "VALIDATION_ERROR", "取消工单必须填写原因")
    completing = payload.status in {"已完成", "completed"} and order.status != "completed"
    if completing and not (payload.action_taken or "").strip():
        raise api_error(422, "VALIDATION_ERROR", "验收工单必须填写实际维修措施")
    if {"root_cause", "action_taken"} & fields and not completing:
        raise api_error(422, "VALIDATION_ERROR", "维修结果只能在验收完成时填写")

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
            elif new_status in {"completed", "cancelled"}:
                order.closed_at = utcnow()

    if "cancel_reason" in fields and order.status != "cancelled":
        raise api_error(422, "VALIDATION_ERROR", "取消原因只能在取消工单时填写")

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
    if "planned_start_at" in fields:
        order.planned_start_at = payload.planned_start_at
    if "due_at" in fields:
        order.due_at = payload.due_at
    _validate_schedule(order.planned_start_at, order.due_at)

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
            "plannedStartAt": order.planned_start_at.isoformat() if order.planned_start_at else None,
            "dueAt": order.due_at.isoformat() if order.due_at else None,
            **({"cancelReason": payload.cancel_reason} if payload.cancel_reason else {}),
        },
    )
    device = db.get(Device, order.device_id)
    try:
        if completing:
            existing_record = db.scalar(
                select(MaintenanceRecord).where(
                    MaintenanceRecord.organization_id
                    == context.organization_id,
                    MaintenanceRecord.work_order_id == order.id,
                    MaintenanceRecord.deleted_at.is_(None),
                )
            )
            if existing_record is None:
                record = MaintenanceRecord(
                    organization_id=context.organization_id,
                    device_id=order.device_id,
                    work_order_id=order.id,
                    diagnosis_id=order.diagnosis_id,
                    alert_id=order.alert_id,
                    record_type="maintenance",
                    summary=order.title[:255],
                    root_cause=payload.root_cause.strip() if payload.root_cause else None,
                    action_taken=payload.action_taken.strip(),
                    recorded_by=context.user_id,
                    recorded_at=utcnow(),
                    created_by=context.user_id,
                    updated_by=context.user_id,
                )
                db.add(record)
                db.flush()
                write_audit(
                    db,
                    organization_id=context.organization_id,
                    actor_user_id=context.user_id,
                    action="maintenance_record.create",
                    entity_type="maintenance_record",
                    entity_id=record.id,
                    after={
                        "deviceId": device.code if device else None,
                        "workOrderId": order.code,
                        "recordType": record.record_type,
                        "actionTaken": record.action_taken,
                    },
                )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(order)

    owner = db.get(User, order.owner_user_id) if order.owner_user_id else None
    alert = db.get(Alert, order.alert_id) if order.alert_id else None
    diagnosis = (
        db.get(Diagnosis, order.diagnosis_id) if order.diagnosis_id else None
    )
    return work_order_to_dict(order, device, owner, alert, diagnosis)

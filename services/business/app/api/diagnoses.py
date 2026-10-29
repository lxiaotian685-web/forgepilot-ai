from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.audit import write_audit
from app.api.codes import next_diagnosis_code, next_work_order_code
from app.api.deps import ROLE_LEVELS, RequestContext, get_context, require_role
from app.api.errors import api_error
from app.api.labels import (
    DIAGNOSIS_STATUS_LABELS,
    RISK_LEVEL_LABELS,
    WORK_ORDER_PRIORITY_LABELS,
    label_to_code,
)
from app.api.serializers import (
    diagnosis_to_dict,
    page_response,
    work_order_to_dict,
)
from app.db import get_db
from app.models import Alert, Device, Diagnosis, Membership, User, WorkOrder, utcnow
from app.schemas.requests import DiagnosisConfirm, DiagnosisCreate

router = APIRouter(prefix="/api/v1/diagnoses", tags=["diagnoses"])


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


def _get_device_by_id(
    db: Session, organization_id: uuid.UUID, device_id: uuid.UUID
) -> Device | None:
    return db.scalar(
        select(Device).where(
            Device.id == device_id,
            Device.organization_id == organization_id,
            Device.deleted_at.is_(None),
        )
    )


def _get_diagnosis(
    db: Session, organization_id: uuid.UUID, code: str
) -> Diagnosis | None:
    return db.scalar(
        select(Diagnosis).where(
            Diagnosis.organization_id == organization_id,
            Diagnosis.code == code,
            Diagnosis.deleted_at.is_(None),
        )
    )


def _get_alert(
    db: Session, organization_id: uuid.UUID, code: str
) -> Alert | None:
    return db.scalar(
        select(Alert).where(
            Alert.organization_id == organization_id,
            Alert.code == code,
            Alert.deleted_at.is_(None),
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


def _load_related(db: Session, organization_id: uuid.UUID, diagnoses: list[Diagnosis]):
    device_ids = {diagnosis.device_id for diagnosis in diagnoses}
    alert_ids = {
        diagnosis.alert_id for diagnosis in diagnoses if diagnosis.alert_id
    }
    confirmer_ids = {
        diagnosis.confirmed_by
        for diagnosis in diagnoses
        if diagnosis.confirmed_by
    }
    diagnosis_ids = [diagnosis.id for diagnosis in diagnoses]

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
    confirmers = (
        {
            user.id: user
            for user in db.scalars(
                select(User).where(User.id.in_(confirmer_ids))
            ).all()
        }
        if confirmer_ids
        else {}
    )
    work_orders = (
        db.scalars(
            select(WorkOrder).where(
                WorkOrder.organization_id == organization_id,
                WorkOrder.diagnosis_id.in_(diagnosis_ids),
                WorkOrder.deleted_at.is_(None),
            )
        ).all()
        if diagnosis_ids
        else []
    )
    work_order_by_diagnosis = {
        order.diagnosis_id: order for order in work_orders
    }
    return devices, alerts, confirmers, work_order_by_diagnosis


@router.post("", status_code=201)
def create_diagnosis(
    payload: DiagnosisCreate,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "technician")
    device = _get_device(db, context.organization_id, payload.device_id)
    if device is None:
        raise api_error(404, "NOT_FOUND", "设备不存在")

    alert = None
    if payload.alert_id:
        alert = _get_alert(db, context.organization_id, payload.alert_id)
        if alert is None:
            raise api_error(
                422,
                "VALIDATION_ERROR",
                "来源告警不存在",
                {"alertId": payload.alert_id},
            )
        if alert.device_id != device.id:
            raise api_error(
                422,
                "VALIDATION_ERROR",
                "来源告警不属于目标设备",
                {"alertId": alert.code, "deviceId": device.code},
            )

    risk_level = label_to_code(
        payload.risk_level or "low", RISK_LEVEL_LABELS, "riskLevel"
    )
    now = utcnow()
    try:
        diagnosis = Diagnosis(
            organization_id=context.organization_id,
            device_id=device.id,
            alert_id=alert.id if alert else None,
            code=next_diagnosis_code(db, context.organization_id, now),
            question=payload.question,
            conclusion=payload.conclusion,
            risk_level=risk_level,
            confidence=payload.confidence,
            evidence=payload.evidence,
            model_source=payload.model_source,
            status="draft",
            created_by=context.user_id,
            updated_by=context.user_id,
        )
        db.add(diagnosis)
        db.flush()
        write_audit(
            db,
            organization_id=context.organization_id,
            actor_user_id=context.user_id,
            action="diagnosis.create",
            entity_type="diagnosis",
            entity_id=diagnosis.id,
            after={
                "code": diagnosis.code,
                "status": diagnosis.status,
                "deviceId": device.code,
                "modelSource": diagnosis.model_source,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(diagnosis)
    return diagnosis_to_dict(diagnosis, device, alert, None, None)


@router.get("")
def list_diagnoses(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = Query(default=None),
    device_id: str | None = Query(default=None, alias="deviceId"),
    q: str | None = Query(default=None),
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    stmt = select(Diagnosis).where(
        Diagnosis.organization_id == context.organization_id,
        Diagnosis.deleted_at.is_(None),
    )
    if status:
        stmt = stmt.where(
            Diagnosis.status
            == label_to_code(status, DIAGNOSIS_STATUS_LABELS, "status")
        )
    if device_id:
        stmt = stmt.join(Device, Diagnosis.device_id == Device.id).where(
            Device.organization_id == context.organization_id,
            Device.code == device_id,
            Device.deleted_at.is_(None),
        )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Diagnosis.code.ilike(like),
                Diagnosis.question.ilike(like),
                Diagnosis.conclusion.ilike(like),
            )
        )

    stmt = stmt.order_by(Diagnosis.updated_at.desc())
    total = (
        db.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        or 0
    )
    rows = db.scalars(
        stmt.offset((page - 1) * page_size).limit(page_size)
    ).all()
    devices, alerts, confirmers, work_order_by_diagnosis = _load_related(
        db, context.organization_id, rows
    )
    items = [
        diagnosis_to_dict(
            diagnosis,
            devices.get(diagnosis.device_id),
            alerts.get(diagnosis.alert_id) if diagnosis.alert_id else None,
            confirmers.get(diagnosis.confirmed_by)
            if diagnosis.confirmed_by
            else None,
            work_order_by_diagnosis.get(diagnosis.id),
        )
        for diagnosis in rows
    ]
    return page_response(items, page, page_size, total)


@router.get("/{diagnosis_id}")
def get_diagnosis(
    diagnosis_id: str,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    diagnosis = _get_diagnosis(db, context.organization_id, diagnosis_id)
    if diagnosis is None:
        raise api_error(404, "NOT_FOUND", "诊断不存在")
    devices, alerts, confirmers, work_order_by_diagnosis = _load_related(
        db, context.organization_id, [diagnosis]
    )
    return diagnosis_to_dict(
        diagnosis,
        devices.get(diagnosis.device_id),
        alerts.get(diagnosis.alert_id) if diagnosis.alert_id else None,
        confirmers.get(diagnosis.confirmed_by)
        if diagnosis.confirmed_by
        else None,
        work_order_by_diagnosis.get(diagnosis.id),
    )


@router.post("/{diagnosis_id}/confirm")
def confirm_diagnosis(
    diagnosis_id: str,
    payload: DiagnosisConfirm | None = None,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "technician")
    diagnosis = _get_diagnosis(db, context.organization_id, diagnosis_id)
    if diagnosis is None:
        raise api_error(404, "NOT_FOUND", "诊断不存在")
    if diagnosis.status == "rejected":
        raise api_error(
            409,
            "INVALID_STATE",
            "诊断已拒绝，不能确认",
            {"diagnosisId": diagnosis.code, "status": diagnosis.status},
        )

    device = _get_device_by_id(
        db, context.organization_id, diagnosis.device_id
    )
    if device is None:
        raise api_error(404, "NOT_FOUND", "设备不存在")

    existing_order = db.scalar(
        select(WorkOrder).where(
            WorkOrder.organization_id == context.organization_id,
            WorkOrder.diagnosis_id == diagnosis.id,
            WorkOrder.deleted_at.is_(None),
        )
    )

    alert = db.get(Alert, diagnosis.alert_id) if diagnosis.alert_id else None
    confirmer = (
        db.get(User, diagnosis.confirmed_by)
        if diagnosis.confirmed_by
        else None
    )
    if diagnosis.status == "confirmed" and existing_order is not None:
        owner = (
            db.get(User, existing_order.owner_user_id)
            if existing_order.owner_user_id
            else None
        )
        return {
            "diagnosis": diagnosis_to_dict(
                diagnosis, device, alert, confirmer, existing_order
            ),
            "workOrder": work_order_to_dict(existing_order, device, owner, alert, diagnosis),
        }

    owner = (
        _validate_owner(db, context.organization_id, payload.owner_id)
        if payload and payload.owner_id
        else None
    )
    priority = label_to_code(
        payload.priority if payload and payload.priority else "P3 中",
        WORK_ORDER_PRIORITY_LABELS,
        "priority",
    )
    title = (
        payload.title if payload and payload.title else None
    ) or f"{device.code} 诊断处理：{diagnosis.conclusion or diagnosis.code}"[:255]
    description = (
        payload.description
        if payload and payload.description is not None
        else diagnosis.conclusion
    )
    if payload and payload.planned_start_at is not None:
        if payload.due_at is None:
            raise api_error(422, "VALIDATION_ERROR", "计划开始时间需要配套结束时间")
        if payload.planned_start_at.date() > payload.due_at.date():
            raise api_error(422, "VALIDATION_ERROR", "计划结束日期不能早于开始日期")

    try:
        if diagnosis.status != "confirmed":
            before = {"status": diagnosis.status}
            diagnosis.status = "confirmed"
            diagnosis.confirmed_by = context.user_id
            diagnosis.confirmed_at = utcnow()
            after = {"status": diagnosis.status}
            if payload and payload.note:
                after["note"] = payload.note
            write_audit(
                db,
                organization_id=context.organization_id,
                actor_user_id=context.user_id,
                action="diagnosis.confirm",
                entity_type="diagnosis",
                entity_id=diagnosis.id,
                before=before,
                after=after,
            )

        if existing_order is None:
            now = utcnow()
            existing_order = WorkOrder(
                organization_id=context.organization_id,
                device_id=diagnosis.device_id,
                alert_id=diagnosis.alert_id,
                diagnosis_id=diagnosis.id,
                code=next_work_order_code(
                    db, context.organization_id, now
                ),
                title=title,
                description=description,
                priority=priority,
                status="pending",
                owner_user_id=owner.id if owner else None,
                planned_start_at=payload.planned_start_at if payload else None,
                due_at=payload.due_at if payload else None,
                created_by=context.user_id,
                updated_by=context.user_id,
            )
            db.add(existing_order)
            db.flush()
            write_audit(
                db,
                organization_id=context.organization_id,
                actor_user_id=context.user_id,
                action="work_order.create",
                entity_type="work_order",
                entity_id=existing_order.id,
                after={
                    "code": existing_order.code,
                    "status": existing_order.status,
                    "priority": existing_order.priority,
                    "deviceId": device.code,
                    "diagnosisId": diagnosis.code,
                },
            )
        db.commit()
    except Exception:
        db.rollback()
        raise

    db.refresh(diagnosis)
    db.refresh(existing_order)
    alert = db.get(Alert, diagnosis.alert_id) if diagnosis.alert_id else None
    confirmer = (
        db.get(User, diagnosis.confirmed_by)
        if diagnosis.confirmed_by
        else None
    )
    return {
        "diagnosis": diagnosis_to_dict(
            diagnosis, device, alert, confirmer, existing_order
        ),
        "workOrder": work_order_to_dict(existing_order, device, owner, alert, diagnosis),
    }

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.audit import write_audit
from app.api.deps import ROLE_LEVELS, RequestContext, get_context, require_role
from app.api.errors import api_error
from app.api.labels import (
    ALERT_LEVEL_LABELS,
    ALERT_STATUS_LABELS,
    label_to_code,
)
from app.api.serializers import alert_to_dict, page_response
from app.db import get_db
from app.models import Alert, Device, Membership, User, utcnow
from app.schemas.requests import AlertAcknowledgeRequest, AlertCreate, AlertUpdate

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])
ALERT_TRANSITIONS = {
    "pending": {"processing", "acknowledged", "closed"},
    "processing": {"closed"},
    "acknowledged": {"processing", "closed"},
    "closed": {"processing"},
}


def _active_owner(db: Session, organization_id: uuid.UUID, user_id: uuid.UUID) -> User:
    membership = db.scalar(select(Membership).where(
        Membership.organization_id == organization_id,
        Membership.user_id == user_id,
        Membership.status == "active",
    ))
    user = db.get(User, user_id)
    if membership is None or user is None or user.status != "active" or ROLE_LEVELS.get(membership.role, -1) < ROLE_LEVELS["technician"]:
        raise api_error(422, "VALIDATION_ERROR", "负责人必须是当前组织的在岗维修人员或更高岗位")
    return user


@router.post("", status_code=201)
def create_alert(
    payload: AlertCreate,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "manager")
    if not payload.title.strip():
        raise api_error(422, "VALIDATION_ERROR", "告警标题不能为空")
    device = db.scalar(select(Device).where(
        Device.organization_id == context.organization_id,
        Device.code == payload.device_id,
        Device.deleted_at.is_(None),
    ))
    if device is None:
        raise api_error(404, "NOT_FOUND", "设备不存在")
    level = label_to_code(payload.level, ALERT_LEVEL_LABELS, "level")
    owner = _active_owner(db, context.organization_id, payload.owner_id) if payload.owner_id else None
    alert = Alert(
        organization_id=context.organization_id,
        device_id=device.id,
        code=f"ALT-{uuid.uuid4().hex[:12].upper()}",
        title=payload.title.strip(),
        description=payload.description,
        level=level,
        status="pending",
        owner_user_id=owner.id if owner else None,
        source="manual",
        created_by=context.user_id,
        updated_by=context.user_id,
    )
    db.add(alert)
    db.flush()
    write_audit(db, organization_id=context.organization_id, actor_user_id=context.user_id,
                action="alert.create", entity_type="alert", entity_id=alert.id,
                after={"code": alert.code, "deviceId": device.code, "level": level, "ownerId": str(owner.id) if owner else None})
    db.commit()
    return alert_to_dict(alert, device, owner)


@router.patch("/{alert_id}")
def update_alert(
    alert_id: str,
    payload: AlertUpdate,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "technician")
    alert = db.scalar(select(Alert).where(
        Alert.organization_id == context.organization_id,
        Alert.code == alert_id,
        Alert.deleted_at.is_(None),
    ))
    if alert is None:
        raise api_error(404, "NOT_FOUND", "告警不存在")
    fields = payload.model_fields_set
    if ROLE_LEVELS.get(context.role, -1) < ROLE_LEVELS["manager"] and alert.owner_user_id != context.user_id:
        raise api_error(403, "FORBIDDEN", "只能处理指派给自己的告警")
    if fields & {"title", "level", "description", "owner_id"}:
        require_role(context, "manager")
    before = {"title": alert.title, "level": alert.level, "status": alert.status,
              "ownerId": str(alert.owner_user_id) if alert.owner_user_id else None}
    if "title" in fields and payload.title is not None:
        if not payload.title.strip():
            raise api_error(422, "VALIDATION_ERROR", "告警标题不能为空")
        alert.title = payload.title.strip()
    if "level" in fields and payload.level is not None:
        alert.level = label_to_code(payload.level, ALERT_LEVEL_LABELS, "level")
    if "description" in fields:
        alert.description = payload.description
    if "owner_id" in fields:
        alert.owner_user_id = _active_owner(db, context.organization_id, payload.owner_id).id if payload.owner_id else None
    if "status" in fields and payload.status is not None:
        new_status = label_to_code(payload.status, ALERT_STATUS_LABELS, "status")
        if new_status != alert.status:
            if new_status not in ALERT_TRANSITIONS[alert.status]:
                raise api_error(409, "INVALID_TRANSITION", "告警状态流转不合法")
            if alert.status == "closed" or new_status == "closed":
                require_role(context, "manager")
            if new_status == "processing" and alert.owner_user_id is None:
                raise api_error(422, "VALIDATION_ERROR", "进入处理中前必须指派负责人")
            alert.status = new_status
            if new_status == "acknowledged":
                alert.acknowledged_at = utcnow()
                alert.acknowledged_by = context.user_id
    alert.updated_by = context.user_id
    after = {"title": alert.title, "level": alert.level, "status": alert.status,
             "ownerId": str(alert.owner_user_id) if alert.owner_user_id else None}
    write_audit(db, organization_id=context.organization_id, actor_user_id=context.user_id,
                action="alert.update", entity_type="alert", entity_id=alert.id, before=before, after=after)
    db.commit()
    device = db.get(Device, alert.device_id)
    owner = db.get(User, alert.owner_user_id) if alert.owner_user_id else None
    return alert_to_dict(alert, device, owner)


def _load_related(db: Session, alerts: list[Alert]):
    device_ids = {alert.device_id for alert in alerts}
    owner_ids = {
        alert.owner_user_id for alert in alerts if alert.owner_user_id is not None
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
def list_alerts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = Query(default=None),
    level: str | None = Query(default=None),
    device_id: str | None = Query(default=None, alias="deviceId"),
    q: str | None = Query(default=None),
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    stmt = select(Alert).where(
        Alert.organization_id == context.organization_id,
        Alert.deleted_at.is_(None),
    )
    if status:
        stmt = stmt.where(
            Alert.status == label_to_code(status, ALERT_STATUS_LABELS, "status")
        )
    if level:
        stmt = stmt.where(
            Alert.level == label_to_code(level, ALERT_LEVEL_LABELS, "level")
        )
    if device_id:
        stmt = stmt.join(Device, Alert.device_id == Device.id).where(
            Device.organization_id == context.organization_id,
            Device.code == device_id,
            Device.deleted_at.is_(None),
        )
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Alert.code.ilike(like), Alert.title.ilike(like)))

    stmt = stmt.order_by(Alert.occurred_at.desc())
    total = (
        db.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        or 0
    )
    alerts = db.scalars(
        stmt.offset((page - 1) * page_size).limit(page_size)
    ).all()
    devices, owners = _load_related(db, alerts)
    items = [
        alert_to_dict(
            alert,
            devices.get(alert.device_id),
            owners.get(alert.owner_user_id) if alert.owner_user_id else None,
        )
        for alert in alerts
    ]
    return page_response(items, page, page_size, total)


@router.post("/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    payload: AlertAcknowledgeRequest | None = None,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "technician")
    alert = db.scalar(
        select(Alert).where(
            Alert.organization_id == context.organization_id,
            Alert.code == alert_id,
            Alert.deleted_at.is_(None),
        )
    )
    if alert is None:
        raise api_error(404, "NOT_FOUND", "告警不存在")
    if alert.status == "closed":
        raise api_error(
            409,
            "INVALID_STATE",
            "告警已关闭，不能再次确认",
            {
                "alertId": alert.code,
                "status": ALERT_STATUS_LABELS.get(alert.status, alert.status),
            },
        )

    if alert.status != "acknowledged":
        before = {"status": alert.status}
        alert.status = "acknowledged"
        alert.acknowledged_at = utcnow()
        alert.acknowledged_by = context.user_id
        if alert.owner_user_id is None:
            alert.owner_user_id = context.user_id
        after = {"status": alert.status}
        if payload and payload.note:
            after["note"] = payload.note
        write_audit(
            db,
            organization_id=context.organization_id,
            actor_user_id=context.user_id,
            action="alert.acknowledge",
            entity_type="alert",
            entity_id=alert.id,
            before=before,
            after=after,
        )
        db.commit()
        db.refresh(alert)

    device = db.get(Device, alert.device_id)
    owner = db.get(User, alert.owner_user_id) if alert.owner_user_id else None
    return alert_to_dict(alert, device, owner)

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import RequestContext, get_context
from app.api.errors import api_error
from app.api.labels import (
    ALERT_LEVEL_LABELS,
    ALERT_STATUS_LABELS,
    label_to_code,
)
from app.api.serializers import iso, page_response
from app.db import get_db
from app.models import (
    Alert,
    Device,
    Diagnosis,
    MaintenanceRecord,
    WorkOrder,
)

router = APIRouter(prefix="/api/v1/devices", tags=["faults"])


@router.get("/{device_id}/faults")
def list_device_faults(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = Query(default=None),
    level: str | None = Query(default=None),
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    device = db.scalar(
        select(Device).where(
            Device.organization_id == context.organization_id,
            Device.code == device_id,
            Device.deleted_at.is_(None),
        )
    )
    if device is None:
        raise api_error(404, "NOT_FOUND", "设备不存在")

    stmt = select(Alert).where(
        Alert.organization_id == context.organization_id,
        Alert.device_id == device.id,
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
    if from_time:
        stmt = stmt.where(Alert.occurred_at >= from_time)
    if to_time:
        stmt = stmt.where(Alert.occurred_at <= to_time)
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
    alert_ids = {alert.id for alert in alerts}

    diagnoses = (
        db.scalars(
            select(Diagnosis)
            .where(
                Diagnosis.organization_id == context.organization_id,
                Diagnosis.alert_id.in_(alert_ids),
                Diagnosis.deleted_at.is_(None),
            )
            .order_by(Diagnosis.updated_at.desc())
        ).all()
        if alert_ids
        else []
    )
    diagnosis_by_alert: dict = {}
    for diagnosis in diagnoses:
        diagnosis_by_alert.setdefault(diagnosis.alert_id, diagnosis)
    diagnosis_ids = {
        diagnosis.id for diagnosis in diagnosis_by_alert.values()
    }

    orders = (
        db.scalars(
            select(WorkOrder)
            .where(
                WorkOrder.organization_id == context.organization_id,
                WorkOrder.deleted_at.is_(None),
                or_(
                    WorkOrder.alert_id.in_(alert_ids),
                    WorkOrder.diagnosis_id.in_(diagnosis_ids or []),
                ),
            )
            .order_by(WorkOrder.updated_at.desc())
        ).all()
        if alert_ids or diagnosis_ids
        else []
    )
    order_by_alert: dict = {}
    order_by_diagnosis: dict = {}
    for order in orders:
        if order.alert_id:
            order_by_alert.setdefault(order.alert_id, order)
        if order.diagnosis_id:
            order_by_diagnosis.setdefault(order.diagnosis_id, order)
    order_ids = {order.id for order in orders}

    records = (
        db.scalars(
            select(MaintenanceRecord)
            .where(
                MaintenanceRecord.organization_id
                == context.organization_id,
                MaintenanceRecord.deleted_at.is_(None),
                or_(
                    MaintenanceRecord.alert_id.in_(alert_ids),
                    MaintenanceRecord.work_order_id.in_(order_ids or []),
                ),
            )
            .order_by(MaintenanceRecord.recorded_at.desc())
        ).all()
        if alert_ids or order_ids
        else []
    )
    record_by_alert: dict = {}
    record_by_order: dict = {}
    for record in records:
        if record.alert_id:
            record_by_alert.setdefault(record.alert_id, record)
        if record.work_order_id:
            record_by_order.setdefault(record.work_order_id, record)

    items = []
    for alert in alerts:
        diagnosis = diagnosis_by_alert.get(alert.id)
        order = order_by_alert.get(alert.id) or (
            order_by_diagnosis.get(diagnosis.id) if diagnosis else None
        )
        record = record_by_alert.get(alert.id) or (
            record_by_order.get(order.id) if order else None
        )
        resolved_at = None
        if order and order.closed_at:
            resolved_at = iso(order.closed_at)
        elif record:
            resolved_at = iso(record.recorded_at)
        items.append(
            {
                "alertId": alert.code,
                "deviceId": device.code,
                "level": ALERT_LEVEL_LABELS.get(
                    alert.level, alert.level
                ),
                "title": alert.title,
                "status": ALERT_STATUS_LABELS.get(
                    alert.status, alert.status
                ),
                "occurredAt": iso(alert.occurred_at),
                "diagnosisId": diagnosis.code if diagnosis else None,
                "workOrderId": order.code if order else None,
                "maintenanceRecordId": str(record.id) if record else None,
                "resolvedAt": resolved_at,
            }
        )
    return page_response(items, page, page_size, total)

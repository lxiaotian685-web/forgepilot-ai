from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import RequestContext, get_context
from app.api.labels import RECORD_TYPE_LABELS, label_to_code
from app.api.serializers import maintenance_record_to_dict, page_response
from app.db import get_db
from app.models import (
    Alert,
    Device,
    Diagnosis,
    MaintenanceRecord,
    User,
    WorkOrder,
)

router = APIRouter(
    prefix="/api/v1/maintenance-records", tags=["maintenance"]
)


def _load_related(
    db: Session, organization_id: uuid.UUID, records: list[MaintenanceRecord]
):
    device_ids = {record.device_id for record in records}
    work_order_ids = {
        record.work_order_id for record in records if record.work_order_id
    }
    diagnosis_ids = {
        record.diagnosis_id for record in records if record.diagnosis_id
    }
    alert_ids = {record.alert_id for record in records if record.alert_id}
    actor_ids = {
        record.recorded_by for record in records if record.recorded_by
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
    work_orders = (
        {
            order.id: order
            for order in db.scalars(
                select(WorkOrder).where(
                    WorkOrder.id.in_(work_order_ids),
                    WorkOrder.organization_id == organization_id,
                )
            ).all()
        }
        if work_order_ids
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
    actors = (
        {
            user.id: user
            for user in db.scalars(
                select(User).where(User.id.in_(actor_ids))
            ).all()
        }
        if actor_ids
        else {}
    )
    return devices, work_orders, diagnoses, alerts, actors


@router.get("")
def list_maintenance_records(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    device_id: str | None = Query(default=None, alias="deviceId"),
    work_order_id: str | None = Query(default=None, alias="workOrderId"),
    record_type: str | None = Query(default=None, alias="recordType"),
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    stmt = select(MaintenanceRecord).where(
        MaintenanceRecord.organization_id == context.organization_id,
        MaintenanceRecord.deleted_at.is_(None),
    )
    if device_id:
        stmt = stmt.join(
            Device, MaintenanceRecord.device_id == Device.id
        ).where(
            Device.organization_id == context.organization_id,
            Device.code == device_id,
            Device.deleted_at.is_(None),
        )
    if work_order_id:
        stmt = stmt.join(
            WorkOrder, MaintenanceRecord.work_order_id == WorkOrder.id
        ).where(
            WorkOrder.organization_id == context.organization_id,
            WorkOrder.code == work_order_id,
            WorkOrder.deleted_at.is_(None),
        )
    if record_type:
        stmt = stmt.where(
            MaintenanceRecord.record_type
            == label_to_code(record_type, RECORD_TYPE_LABELS, "recordType")
        )
    if from_time:
        stmt = stmt.where(MaintenanceRecord.recorded_at >= from_time)
    if to_time:
        stmt = stmt.where(MaintenanceRecord.recorded_at <= to_time)

    stmt = stmt.order_by(MaintenanceRecord.recorded_at.desc())
    total = (
        db.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        or 0
    )
    rows = db.scalars(
        stmt.offset((page - 1) * page_size).limit(page_size)
    ).all()
    devices, work_orders, diagnoses, alerts, actors = _load_related(
        db, context.organization_id, rows
    )
    items = [
        maintenance_record_to_dict(
            record,
            devices.get(record.device_id),
            work_orders.get(record.work_order_id)
            if record.work_order_id
            else None,
            diagnoses.get(record.diagnosis_id)
            if record.diagnosis_id
            else None,
            alerts.get(record.alert_id) if record.alert_id else None,
            actors.get(record.recorded_by) if record.recorded_by else None,
        )
        for record in rows
    ]
    return page_response(items, page, page_size, total)

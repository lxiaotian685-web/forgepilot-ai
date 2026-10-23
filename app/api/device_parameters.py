from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.audit import write_audit
from app.api.deps import RequestContext, get_context, require_role
from app.api.errors import api_error
from app.api.labels import PARAMETER_SOURCES
from app.api.serializers import device_parameter_to_dict, page_response
from app.db import get_db
from app.models import Device, DeviceParameter, utcnow
from app.schemas.requests import DeviceParameterCreate, DeviceParameterUpdate

router = APIRouter(prefix="/api/v1/devices", tags=["device-parameters"])


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


def _get_parameter(
    db: Session,
    organization_id: uuid.UUID,
    device_id: uuid.UUID,
    parameter_id: uuid.UUID,
) -> DeviceParameter | None:
    return db.scalar(
        select(DeviceParameter).where(
            DeviceParameter.id == parameter_id,
            DeviceParameter.organization_id == organization_id,
            DeviceParameter.device_id == device_id,
            DeviceParameter.deleted_at.is_(None),
        )
    )


def _validate_source(source: str) -> None:
    if source not in PARAMETER_SOURCES:
        raise api_error(
            422,
            "VALIDATION_ERROR",
            "source 取值不合法",
            {"field": "source", "allowed": sorted(PARAMETER_SOURCES)},
        )


def _duplicate_exists(
    db: Session,
    organization_id: uuid.UUID,
    device_id: uuid.UUID,
    name: str,
    recorded_at: datetime,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    stmt = select(DeviceParameter.id).where(
        DeviceParameter.organization_id == organization_id,
        DeviceParameter.device_id == device_id,
        DeviceParameter.name == name,
        DeviceParameter.recorded_at == recorded_at,
        DeviceParameter.deleted_at.is_(None),
    )
    if exclude_id is not None:
        stmt = stmt.where(DeviceParameter.id != exclude_id)
    return db.scalar(stmt) is not None


@router.get("/{device_id}/parameters")
def list_device_parameters(
    device_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    name: str | None = Query(default=None),
    source: str | None = Query(default=None),
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    latest: bool = Query(default=False),
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    device = _get_device(db, context.organization_id, device_id)
    if device is None:
        raise api_error(404, "NOT_FOUND", "设备不存在")

    stmt = select(DeviceParameter).where(
        DeviceParameter.organization_id == context.organization_id,
        DeviceParameter.device_id == device.id,
        DeviceParameter.deleted_at.is_(None),
    )
    if name:
        stmt = stmt.where(DeviceParameter.name == name)
    if source:
        _validate_source(source)
        stmt = stmt.where(DeviceParameter.source == source)
    if from_time:
        stmt = stmt.where(DeviceParameter.recorded_at >= from_time)
    if to_time:
        stmt = stmt.where(DeviceParameter.recorded_at <= to_time)
    stmt = stmt.order_by(DeviceParameter.recorded_at.desc())
    rows = db.scalars(stmt).all()

    if latest:
        seen: set[str] = set()
        deduped = []
        for row in rows:
            if row.name in seen:
                continue
            seen.add(row.name)
            deduped.append(row)
        rows = deduped

    total = len(rows)
    start = (page - 1) * page_size
    page_rows = rows[start : start + page_size]
    items = [
        device_parameter_to_dict(parameter, device)
        for parameter in page_rows
    ]
    return page_response(items, page, page_size, total)


@router.post("/{device_id}/parameters", status_code=201)
def create_device_parameter(
    device_id: str,
    payload: DeviceParameterCreate,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "technician")
    device = _get_device(db, context.organization_id, device_id)
    if device is None:
        raise api_error(404, "NOT_FOUND", "设备不存在")
    _validate_source(payload.source)

    recorded_at = payload.recorded_at or utcnow()
    if _duplicate_exists(
        db,
        context.organization_id,
        device.id,
        payload.name,
        recorded_at,
    ):
        raise api_error(
            409,
            "CONFLICT",
            "同一设备、参数名和采集时间已存在",
            {"name": payload.name, "recordedAt": recorded_at.isoformat()},
        )

    is_authoritative = (
        False
        if payload.source == "model_inference"
        else (
            payload.is_authoritative
            if payload.is_authoritative is not None
            else True
        )
    )
    try:
        parameter = DeviceParameter(
            organization_id=context.organization_id,
            device_id=device.id,
            name=payload.name,
            value=payload.value,
            unit=payload.unit,
            source=payload.source,
            source_ref=payload.source_ref,
            is_authoritative=is_authoritative,
            recorded_at=recorded_at,
            created_by=context.user_id,
            updated_by=context.user_id,
        )
        db.add(parameter)
        db.flush()
        write_audit(
            db,
            organization_id=context.organization_id,
            actor_user_id=context.user_id,
            action="device_parameter.create",
            entity_type="device_parameter",
            entity_id=parameter.id,
            after={
                "deviceId": device.code,
                "name": parameter.name,
                "value": float(parameter.value),
                "unit": parameter.unit,
                "source": parameter.source,
                "isAuthoritative": parameter.is_authoritative,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(parameter)
    return device_parameter_to_dict(parameter, device)


@router.patch("/{device_id}/parameters/{parameter_id}")
def update_device_parameter(
    device_id: str,
    parameter_id: uuid.UUID,
    payload: DeviceParameterUpdate,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "technician")
    device = _get_device(db, context.organization_id, device_id)
    if device is None:
        raise api_error(404, "NOT_FOUND", "设备不存在")
    parameter = _get_parameter(
        db, context.organization_id, device.id, parameter_id
    )
    if parameter is None:
        raise api_error(404, "NOT_FOUND", "参数不存在")

    fields = payload.model_fields_set
    before = {
        "value": float(parameter.value),
        "unit": parameter.unit,
        "source": parameter.source,
        "sourceRef": parameter.source_ref,
        "isAuthoritative": parameter.is_authoritative,
        "recordedAt": parameter.recorded_at.isoformat(),
    }

    new_source = parameter.source
    if "source" in fields and payload.source is not None:
        _validate_source(payload.source)
        new_source = payload.source
    new_recorded_at = (
        payload.recorded_at
        if "recorded_at" in fields and payload.recorded_at is not None
        else parameter.recorded_at
    )
    if _duplicate_exists(
        db,
        context.organization_id,
        device.id,
        parameter.name,
        new_recorded_at,
        exclude_id=parameter.id,
    ):
        raise api_error(
            409,
            "CONFLICT",
            "同一设备、参数名和采集时间已存在",
            {
                "name": parameter.name,
                "recordedAt": new_recorded_at.isoformat(),
            },
        )

    if "value" in fields and payload.value is not None:
        parameter.value = payload.value
    if "unit" in fields:
        parameter.unit = payload.unit
    if "source_ref" in fields:
        parameter.source_ref = payload.source_ref
    if "recorded_at" in fields and payload.recorded_at is not None:
        parameter.recorded_at = payload.recorded_at
    parameter.source = new_source
    if new_source == "model_inference":
        parameter.is_authoritative = False
    elif "is_authoritative" in fields and payload.is_authoritative is not None:
        parameter.is_authoritative = payload.is_authoritative
    parameter.updated_by = context.user_id

    try:
        write_audit(
            db,
            organization_id=context.organization_id,
            actor_user_id=context.user_id,
            action="device_parameter.update",
            entity_type="device_parameter",
            entity_id=parameter.id,
            before=before,
            after={
                "deviceId": device.code,
                "name": parameter.name,
                "value": float(parameter.value),
                "unit": parameter.unit,
                "source": parameter.source,
                "isAuthoritative": parameter.is_authoritative,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    db.refresh(parameter)
    return device_parameter_to_dict(parameter, device)


@router.delete("/{device_id}/parameters/{parameter_id}", status_code=204)
def delete_device_parameter(
    device_id: str,
    parameter_id: uuid.UUID,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "manager")
    device = _get_device(db, context.organization_id, device_id)
    if device is None:
        raise api_error(404, "NOT_FOUND", "设备不存在")
    parameter = _get_parameter(
        db, context.organization_id, device.id, parameter_id
    )
    if parameter is None:
        raise api_error(404, "NOT_FOUND", "参数不存在")

    parameter.deleted_at = utcnow()
    parameter.updated_by = context.user_id
    try:
        write_audit(
            db,
            organization_id=context.organization_id,
            actor_user_id=context.user_id,
            action="device_parameter.delete",
            entity_type="device_parameter",
            entity_id=parameter.id,
            before={
                "deviceId": device.code,
                "name": parameter.name,
                "value": float(parameter.value),
                "unit": parameter.unit,
                "source": parameter.source,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return None

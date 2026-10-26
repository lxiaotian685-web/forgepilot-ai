from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.audit import write_audit
from app.api.deps import RequestContext, get_context, require_role
from app.api.errors import api_error
from app.api.labels import DEVICE_STATE_LABELS, label_to_code
from app.api.serializers import (
    device_detail_to_dict,
    device_to_dict,
    page_response,
)
from app.db import get_db
from app.models import Alert, Device, Plant
from app.schemas.requests import DeviceImportRequest

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.post("/import", status_code=201)
def import_devices(
    payload: DeviceImportRequest,
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "manager")
    normalized = [item.id.strip().casefold() for item in payload.items]
    if len(set(normalized)) != len(normalized):
        raise api_error(422, "VALIDATION_ERROR", "导入文件内设备编号重复")

    existing = db.scalars(select(Device).where(
        Device.organization_id == context.organization_id,
        Device.deleted_at.is_(None),
    )).all()
    if any(device.code.casefold() in normalized for device in existing):
        raise api_error(409, "CONFLICT", "设备编号已存在")

    plants = db.scalars(select(Plant).where(
        Plant.organization_id == context.organization_id,
        Plant.status == "active",
        Plant.deleted_at.is_(None),
    )).all()
    plant_by_name = {plant.name.casefold(): plant for plant in plants}
    plant_by_code = {plant.code.casefold(): plant for plant in plants}
    rows = []
    for item in payload.items:
        plant_key = item.plant.strip().casefold()
        plant = plant_by_code.get(plant_key) or plant_by_name.get(plant_key)
        if plant is None:
            raise api_error(422, "VALIDATION_ERROR", "厂区不存在或不属于当前组织", {"plant": item.plant})
        rows.append((Device(
            organization_id=context.organization_id,
            plant_id=plant.id,
            code=item.id.strip(),
            name=item.name.strip(),
            type=item.type.strip(),
            location=item.location.strip(),
            state="offline",
            health=100,
            created_by=context.user_id,
            updated_by=context.user_id,
        ), plant))

    try:
        db.add_all([device for device, _ in rows])
        db.flush()
        for device, plant in rows:
            write_audit(
                db,
                organization_id=context.organization_id,
                actor_user_id=context.user_id,
                action="device.import",
                entity_type="device",
                entity_id=device.id,
                after={"code": device.code, "plant": plant.code, "state": "offline"},
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise api_error(409, "CONFLICT", "设备编号已存在，请刷新后重试") from exc
    return {"created": len(rows), "items": [device_to_dict(device, 0, plant) for device, plant in rows]}


def _alert_counts(db: Session, device_ids: list) -> dict:
    if not device_ids:
        return {}
    rows = db.execute(
        select(Alert.device_id, func.count())
        .where(
            Alert.device_id.in_(device_ids),
            Alert.deleted_at.is_(None),
            Alert.status != "closed",
        )
        .group_by(Alert.device_id)
    ).all()
    return {device_id: count for device_id, count in rows}


@router.get("")
def list_devices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    plant_id: str | None = Query(default=None, alias="plantId"),
    state: str | None = Query(default=None),
    type: str | None = Query(default=None),
    q: str | None = Query(default=None),
    sort: str = Query(default="-updatedAt"),
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    stmt = select(Device).where(
        Device.organization_id == context.organization_id,
        Device.deleted_at.is_(None),
    )
    if plant_id:
        stmt = stmt.join(Plant, Device.plant_id == Plant.id).where(
            Plant.organization_id == context.organization_id,
            Plant.code == plant_id,
            Plant.deleted_at.is_(None),
        )
    if state:
        stmt = stmt.where(
            Device.state == label_to_code(state, DEVICE_STATE_LABELS, "state")
        )
    if type:
        stmt = stmt.where(Device.type == type)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Device.code.ilike(like), Device.name.ilike(like)))

    sort_key = sort[1:] if sort.startswith("-") else sort
    columns = {
        "code": Device.code,
        "health": Device.health,
        "updatedAt": Device.updated_at,
    }
    column = columns.get(sort_key)
    if column is None:
        raise api_error(
            422, "VALIDATION_ERROR", "sort 取值不合法", {"field": "sort"}
        )
    stmt = stmt.order_by(column.desc() if sort.startswith("-") else column.asc())

    total = (
        db.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        or 0
    )
    rows = db.scalars(
        stmt.offset((page - 1) * page_size).limit(page_size)
    ).all()
    counts = _alert_counts(db, [device.id for device in rows])
    plant_ids = {device.plant_id for device in rows if device.plant_id}
    plants = {plant.id: plant for plant in db.scalars(select(Plant).where(Plant.id.in_(plant_ids), Plant.organization_id == context.organization_id)).all()} if plant_ids else {}
    items = [device_to_dict(device, counts.get(device.id, 0), plants.get(device.plant_id)) for device in rows]
    return page_response(items, page, page_size, total)


@router.get("/{device_id}")
def get_device(
    device_id: str,
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
    plant = db.get(Plant, device.plant_id) if device.plant_id else None
    counts = _alert_counts(db, [device.id])
    return device_detail_to_dict(device, counts.get(device.id, 0), plant)

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, DeviceParameter, Plant


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _device_base(device: Device, plant: Plant | None) -> dict:
    return {
        "id": device.code,
        "name": device.name,
        "type": device.type,
        "model": device.model,
        "serialNumber": device.serial_number,
        "location": device.location,
        "plantId": plant.code if plant else None,
        "health": float(device.health),
        "state": device.state,
    }


def list_device_facts(
    db: Session, organization_id: uuid.UUID, limit: int = 100
) -> list[dict]:
    devices = db.scalars(
        select(Device)
        .where(
            Device.organization_id == organization_id,
            Device.deleted_at.is_(None),
        )
        .order_by(Device.code)
        .limit(limit)
    ).all()
    plant_ids = {device.plant_id for device in devices if device.plant_id}
    plants = (
        {
            plant.id: plant
            for plant in db.scalars(
                select(Plant).where(
                    Plant.id.in_(plant_ids),
                    Plant.organization_id == organization_id,
                    Plant.deleted_at.is_(None),
                )
            ).all()
        }
        if plant_ids
        else {}
    )
    return [
        _device_base(device, plants.get(device.plant_id))
        for device in devices
    ]


def get_device_facts(
    db: Session, organization_id: uuid.UUID, code: str
) -> dict | None:
    device = db.scalar(
        select(Device).where(
            Device.organization_id == organization_id,
            Device.code == code,
            Device.deleted_at.is_(None),
        )
    )
    if device is None:
        return None
    plant = None
    if device.plant_id:
        plant = db.scalar(
            select(Plant).where(
                Plant.id == device.plant_id,
                Plant.organization_id == organization_id,
                Plant.deleted_at.is_(None),
            )
        )
    parameters = db.scalars(
        select(DeviceParameter)
        .where(
            DeviceParameter.organization_id == organization_id,
            DeviceParameter.device_id == device.id,
            DeviceParameter.deleted_at.is_(None),
            DeviceParameter.is_authoritative.is_(True),
        )
        .order_by(DeviceParameter.recorded_at.desc())
    ).all()
    latest: dict[str, dict] = {}
    for parameter in parameters:
        if parameter.name in latest:
            continue
        latest[parameter.name] = {
            "name": parameter.name,
            "value": float(parameter.value),
            "unit": parameter.unit,
            "source": parameter.source,
            "sourceRef": parameter.source_ref,
            "recordedAt": _iso(parameter.recorded_at),
        }
    facts = _device_base(device, plant)
    facts["parameters"] = list(latest.values())
    return facts

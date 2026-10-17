from __future__ import annotations

from datetime import datetime, timezone

from app.api.labels import (
    ALERT_LEVEL_LABELS,
    ALERT_STATUS_LABELS,
    DEVICE_STATE_LABELS,
    WORK_ORDER_PRIORITY_LABELS,
    WORK_ORDER_STATUS_LABELS,
)
from app.models import Alert, Device, Plant, User, WorkOrder


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def device_to_dict(device: Device, alert_count: int) -> dict:
    return {
        "id": device.code,
        "name": device.name,
        "type": device.type,
        "location": device.location,
        "health": float(device.health),
        "state": DEVICE_STATE_LABELS.get(device.state, device.state),
        "alert": alert_count,
    }


def device_detail_to_dict(
    device: Device, alert_count: int, plant: Plant | None
) -> dict:
    data = device_to_dict(device, alert_count)
    data.update(
        {
            "plantId": plant.code if plant else None,
            "model": device.model,
            "serialNumber": device.serial_number,
            "createdAt": iso(device.created_at),
            "updatedAt": iso(device.updated_at),
        }
    )
    return data


def alert_to_dict(
    alert: Alert, device: Device | None, owner: User | None
) -> dict:
    return {
        "id": alert.code,
        "level": ALERT_LEVEL_LABELS.get(alert.level, alert.level),
        "title": alert.title,
        "device": f"{device.code} {device.name}" if device else None,
        "deviceId": device.code if device else None,
        "time": iso(alert.occurred_at),
        "owner": owner.display_name if owner else None,
        "ownerId": str(alert.owner_user_id) if alert.owner_user_id else None,
        "status": ALERT_STATUS_LABELS.get(alert.status, alert.status),
        "description": alert.description,
        "acknowledgedAt": iso(alert.acknowledged_at),
    }


def work_order_to_dict(
    order: WorkOrder, device: Device | None, owner: User | None
) -> dict:
    return {
        "id": order.code,
        "title": order.title,
        "priority": WORK_ORDER_PRIORITY_LABELS.get(
            order.priority, order.priority
        ),
        "owner": owner.display_name if owner else None,
        "ownerId": str(order.owner_user_id) if order.owner_user_id else None,
        "status": WORK_ORDER_STATUS_LABELS.get(order.status, order.status),
        "updated": iso(order.updated_at),
        "deviceId": device.code if device else None,
        "createdAt": iso(order.created_at),
        "description": order.description,
        "dueAt": iso(order.due_at),
    }


def page_response(
    items: list[dict], page: int, page_size: int, total: int
) -> dict:
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return {
        "items": items,
        "page": page,
        "pageSize": page_size,
        "total": total,
        "totalPages": total_pages,
    }

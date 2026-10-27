from __future__ import annotations

from datetime import datetime, timezone

from app.api.labels import (
    ALERT_LEVEL_LABELS,
    ALERT_STATUS_LABELS,
    DEVICE_STATE_LABELS,
    DIAGNOSIS_STATUS_LABELS,
    RECORD_TYPE_LABELS,
    RISK_LEVEL_LABELS,
    WORK_ORDER_PRIORITY_LABELS,
    WORK_ORDER_STATUS_LABELS,
)
from app.models import (
    Alert,
    AuditLog,
    Device,
    DeviceParameter,
    Diagnosis,
    MaintenanceRecord,
    Membership,
    Plant,
    User,
    WorkOrder,
)


def member_to_dict(
    membership: Membership, user: User, open_work_order_count: int = 0
) -> dict:
    return {
        "id": str(user.id),
        "membershipId": str(membership.id),
        "email": user.email,
        "displayName": user.display_name,
        "role": membership.role,
        "status": membership.status,
        "openWorkOrderCount": open_work_order_count,
        "lastLoginAt": iso(user.last_login_at),
        "createdAt": iso(membership.created_at),
        "updatedAt": iso(membership.updated_at),
    }


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def device_to_dict(device: Device, alert_count: int, plant: Plant | None = None) -> dict:
    return {
        "id": device.code,
        "name": device.name,
        "type": device.type,
        "location": device.location,
        "health": None if device.state == "offline" else float(device.health),
        "state": DEVICE_STATE_LABELS.get(device.state, device.state),
        "alert": alert_count,
        "plant": plant.name if plant else None,
    }


def device_parameter_to_dict(
    parameter: DeviceParameter, device: Device | None
) -> dict:
    return {
        "id": str(parameter.id),
        "deviceId": device.code if device else None,
        "name": parameter.name,
        "value": float(parameter.value),
        "unit": parameter.unit,
        "source": parameter.source,
        "sourceRef": parameter.source_ref,
        "isAuthoritative": parameter.is_authoritative,
        "recordedAt": iso(parameter.recorded_at),
        "createdAt": iso(parameter.created_at),
    }


def device_detail_to_dict(
    device: Device, alert_count: int, plant: Plant | None
) -> dict:
    data = device_to_dict(device, alert_count, plant)
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


def diagnosis_to_dict(
    diagnosis: Diagnosis,
    device: Device | None,
    alert: Alert | None,
    confirmer: User | None,
    work_order: WorkOrder | None,
) -> dict:
    return {
        "id": diagnosis.code,
        "deviceId": device.code if device else None,
        "alertId": alert.code if alert else None,
        "question": diagnosis.question,
        "conclusion": diagnosis.conclusion,
        "riskLevel": RISK_LEVEL_LABELS.get(
            diagnosis.risk_level, diagnosis.risk_level
        ),
        "riskLevelCode": diagnosis.risk_level,
        "confidence": (
            float(diagnosis.confidence)
            if diagnosis.confidence is not None
            else None
        ),
        "modelSource": diagnosis.model_source,
        "evidence": diagnosis.evidence,
        "status": diagnosis.status,
        "statusLabel": DIAGNOSIS_STATUS_LABELS.get(
            diagnosis.status, diagnosis.status
        ),
        "confirmedBy": confirmer.display_name if confirmer else None,
        "confirmedById": (
            str(diagnosis.confirmed_by) if diagnosis.confirmed_by else None
        ),
        "confirmedAt": iso(diagnosis.confirmed_at),
        "workOrderId": work_order.code if work_order else None,
        "createdAt": iso(diagnosis.created_at),
        "updatedAt": iso(diagnosis.updated_at),
    }


def work_order_to_dict(
    order: WorkOrder,
    device: Device | None,
    owner: User | None,
    alert: Alert | None = None,
    diagnosis: Diagnosis | None = None,
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
        "alertId": alert.code if alert else None,
        "diagnosisId": diagnosis.code if diagnosis else None,
        "createdAt": iso(order.created_at),
        "description": order.description,
        "plannedStartAt": iso(order.planned_start_at),
        "dueAt": iso(order.due_at),
    }


def audit_event_to_dict(entry: AuditLog, actor: User | None) -> dict:
    entity_id = str(entry.entity_id) if entry.entity_id else None
    return {
        "id": str(entry.id),
        "time": iso(entry.created_at),
        "user": actor.display_name if actor else "系统",
        "userId": str(entry.actor_user_id) if entry.actor_user_id else None,
        "action": entry.action,
        "entityType": entry.entity_type,
        "entityId": entity_id,
        "object": (
            f"{entry.entity_type}:{entity_id}"
            if entity_id
            else entry.entity_type
        ),
        "result": "成功",
        "before": entry.before,
        "after": entry.after,
    }


def maintenance_record_to_dict(
    record: MaintenanceRecord,
    device: Device | None,
    work_order: WorkOrder | None,
    diagnosis: Diagnosis | None,
    alert: Alert | None,
    actor: User | None,
) -> dict:
    return {
        "id": str(record.id),
        "deviceId": device.code if device else None,
        "workOrderId": work_order.code if work_order else None,
        "diagnosisId": diagnosis.code if diagnosis else None,
        "alertId": alert.code if alert else None,
        "recordType": RECORD_TYPE_LABELS.get(
            record.record_type, record.record_type
        ),
        "recordTypeCode": record.record_type,
        "summary": record.summary,
        "rootCause": record.root_cause,
        "actionTaken": record.action_taken,
        "recordedBy": actor.display_name if actor else None,
        "recordedById": (
            str(record.recorded_by) if record.recorded_by else None
        ),
        "recordedAt": iso(record.recorded_at),
        "createdAt": iso(record.created_at),
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

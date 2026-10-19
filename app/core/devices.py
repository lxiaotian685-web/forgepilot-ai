from __future__ import annotations

DEVICE_MODEL_MAP: dict[str, str] = {
    "AC-07": "motor-001",
    "P-102": "compressor-002",
    "CNC-01": "cnc-003",
}


def resolve_equipment_model(
    device_id: str, equipment_model: str | None = None
) -> str | None:
    if equipment_model:
        return equipment_model
    return DEVICE_MODEL_MAP.get(device_id)

from __future__ import annotations

DEVICE_CATALOG: dict[str, dict[str, str]] = {
    "AC-07": {"model": "GX11", "category": "screw_air_compressor"},
    "P-102": {"model": "P-102X", "category": "centrifugal_pump"},
    "CNC-04": {"model": "CNC-04", "category": "cnc_machine"},
}

DOC_CATEGORY: dict[str, str] = {
    "compressor-002": "screw_air_compressor",
    "pump-004": "centrifugal_pump",
    "cnc-003": "cnc_machine",
}

CATEGORY_DOC_MODEL = {category: model for model, category in DOC_CATEGORY.items()}


def resolve_equipment_model(
    device_id: str, equipment_model: str | None = None
) -> tuple[str | None, str]:
    if equipment_model:
        return equipment_model, "ok"
    info = DEVICE_CATALOG.get(device_id)
    if info is None:
        return None, "device_not_found"
    model = CATEGORY_DOC_MODEL.get(info["category"])
    if model is None:
        return None, "no_knowledge"
    return model, "ok"

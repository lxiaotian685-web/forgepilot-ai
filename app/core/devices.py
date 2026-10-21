from __future__ import annotations

DEVICE_CATALOG: dict[str, dict[str, str]] = {
    "AC-07": {
        "name": "螺杆空气压缩机",
        "model": "GX11",
        "category": "screw_air_compressor",
        "type": "动力与流体机械",
        "location": "压缩站 Bay03",
        "status": "attention",
    },
    "P-102": {
        "name": "高压离心注水泵",
        "model": "P-102X",
        "category": "centrifugal_pump",
        "type": "流体动力系统",
        "location": "冷却循环水站",
        "status": "attention",
    },
    "CNC-04": {
        "name": "数控龙门铣床",
        "model": "GMC-4000",
        "category": "cnc_machine",
        "type": "精密加工单元",
        "location": "重载加工岛 #3",
        "status": "alert",
    },
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
    info = DEVICE_CATALOG.get(device_id)
    if info is None:
        return None, "device_not_found"
    model = CATEGORY_DOC_MODEL.get(info["category"])
    if model is None:
        return None, "no_knowledge"
    if equipment_model is not None and equipment_model != model:
        return None, "model_mismatch"
    return model, "ok"

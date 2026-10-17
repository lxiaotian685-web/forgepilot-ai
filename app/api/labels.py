from __future__ import annotations

from app.api.errors import api_error

DEVICE_STATE_LABELS = {
    "running": "运行正常",
    "attention": "需关注",
    "alert": "告警异常",
    "offline": "离线",
}

ALERT_LEVEL_LABELS = {
    "p1": "一级紧急",
    "p2": "二级警告",
    "p3": "三级提示",
}

ALERT_STATUS_LABELS = {
    "pending": "待确认",
    "processing": "处理中",
    "acknowledged": "已确认",
    "closed": "已关闭",
}

WORK_ORDER_PRIORITY_LABELS = {
    "p1": "P1 紧急",
    "p2": "P2 高",
    "p3": "P3 中",
    "p4": "P4 低",
}

WORK_ORDER_STATUS_LABELS = {
    "pending": "待处理",
    "processing": "处理中",
    "verifying": "待验收",
    "completed": "已完成",
    "cancelled": "已取消",
}

WORK_ORDER_TRANSITIONS = {
    "pending": {"processing", "cancelled"},
    "processing": {"verifying", "cancelled"},
    "verifying": {"completed", "processing"},
    "completed": set(),
    "cancelled": set(),
}


def label_to_code(value: str, labels: dict[str, str], field: str) -> str:
    if value in labels:
        return value
    reverse = {label: code for code, label in labels.items()}
    if value in reverse:
        return reverse[value]
    raise api_error(
        422,
        "VALIDATION_ERROR",
        f"{field} 取值不合法",
        {"field": field, "allowed": list(reverse)},
    )

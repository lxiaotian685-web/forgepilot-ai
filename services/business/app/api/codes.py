from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.models import Diagnosis, WorkOrder


def _next_code(
    db: Session,
    model,
    organization_id: uuid.UUID,
    prefix: str,
    now: datetime,
) -> str:
    base = f"{prefix}-{now:%Y%m%d}-"
    existing = (
        db.scalar(
            select(func.count())
            .select_from(model)
            .where(
                model.organization_id == organization_id,
                model.code.like(f"{base}%"),
            )
        )
        or 0
    )
    sequence = existing + 1
    for _ in range(100):
        code = f"{base}{sequence:02d}"
        found = db.scalar(
            select(model.id).where(
                model.organization_id == organization_id,
                model.code == code,
            )
        )
        if found is None:
            return code
        sequence += 1
    raise api_error(409, "CONFLICT", "无法生成唯一编号")


def next_work_order_code(
    db: Session, organization_id: uuid.UUID, now: datetime
) -> str:
    return _next_code(db, WorkOrder, organization_id, "WO", now)


def next_diagnosis_code(
    db: Session, organization_id: uuid.UUID, now: datetime
) -> str:
    return _next_code(db, Diagnosis, organization_id, "DIAG", now)

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import RequestContext, get_context, require_role
from app.api.serializers import audit_event_to_dict, page_response
from app.db import get_db
from app.models import AuditLog, User

router = APIRouter(prefix="/api/v1/audit-events", tags=["audit"])


@router.get("")
def list_audit_events(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None, alias="entityType"),
    entity_id: uuid.UUID | None = Query(default=None, alias="entityId"),
    actor_id: uuid.UUID | None = Query(default=None, alias="actorId"),
    from_time: datetime | None = Query(default=None, alias="from"),
    to_time: datetime | None = Query(default=None, alias="to"),
    q: str | None = Query(default=None),
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "manager")
    stmt = select(AuditLog).where(
        AuditLog.organization_id == context.organization_id
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_user_id == actor_id)
    if from_time:
        stmt = stmt.where(AuditLog.created_at >= from_time)
    if to_time:
        stmt = stmt.where(AuditLog.created_at <= to_time)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                AuditLog.action.ilike(like),
                AuditLog.entity_type.ilike(like),
            )
        )

    stmt = stmt.order_by(AuditLog.created_at.desc())
    total = (
        db.scalar(
            select(func.count()).select_from(stmt.order_by(None).subquery())
        )
        or 0
    )
    rows = db.scalars(
        stmt.offset((page - 1) * page_size).limit(page_size)
    ).all()
    actor_ids = {
        entry.actor_user_id for entry in rows if entry.actor_user_id
    }
    actors = (
        {
            user.id: user
            for user in db.scalars(
                select(User).where(User.id.in_(actor_ids))
            ).all()
        }
        if actor_ids
        else {}
    )
    items = [
        audit_event_to_dict(
            entry,
            actors.get(entry.actor_user_id) if entry.actor_user_id else None,
        )
        for entry in rows
    ]
    return page_response(items, page, page_size, total)

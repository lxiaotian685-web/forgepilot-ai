from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.audit import write_audit
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
    include_internal: bool = Query(False, alias="includeInternal"),
    context: RequestContext = Depends(get_context),
    db: Session = Depends(get_db),
):
    require_role(context, "manager")
    stmt = select(AuditLog).where(
        AuditLog.organization_id == context.organization_id
    )
    archived = select(AuditLog.entity_id).where(
        AuditLog.organization_id == context.organization_id,
        AuditLog.action == "audit.archive",
        AuditLog.entity_id.is_not(None),
    )
    stmt = stmt.where(AuditLog.id.not_in(archived))
    if not include_internal:
        stmt = stmt.where(AuditLog.action.not_in(["audit.archive", "audit.annotate"]))
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
    for item in items:
        correction = db.scalar(select(AuditLog).where(
            AuditLog.organization_id == context.organization_id,
            AuditLog.action == "audit.annotate",
            AuditLog.entity_id == uuid.UUID(item["id"]),
        ).order_by(AuditLog.created_at.desc()))
        item["annotation"] = correction.after if correction else None
    return page_response(items, page, page_size, total)


class AuditAnnotation(BaseModel):
    ownerName: str = Field(default="", max_length=100)
    note: str = Field(default="", max_length=2000)


@router.patch("/{event_id}")
def annotate_audit_event(event_id: uuid.UUID, payload: AuditAnnotation,
                         context: RequestContext = Depends(get_context),
                         db: Session = Depends(get_db)):
    require_role(context, "admin")
    entry = db.scalar(select(AuditLog).where(
        AuditLog.id == event_id, AuditLog.organization_id == context.organization_id))
    if entry is None:
        raise HTTPException(404, "审计记录不存在")
    if entry.action in ("audit.archive", "audit.annotate"):
        raise HTTPException(409, "操作留痕不可修改")
    archived = db.scalar(select(AuditLog).where(
        AuditLog.organization_id == context.organization_id,
        AuditLog.action == "audit.archive", AuditLog.entity_id == event_id))
    if archived:
        raise HTTPException(409, "记录已删除，请刷新列表")
    previous = db.scalar(select(AuditLog).where(
        AuditLog.organization_id == context.organization_id,
        AuditLog.action == "audit.annotate", AuditLog.entity_id == event_id,
    ).order_by(AuditLog.created_at.desc()))
    annotation = {"ownerName": payload.ownerName.strip(), "note": payload.note.strip()}
    write_audit(db, organization_id=context.organization_id,
                actor_user_id=context.user_id, action="audit.annotate",
                entity_type="audit", entity_id=event_id,
                before=previous.after if previous else {}, after=annotation)
    db.commit()
    return {"id": str(event_id), "annotation": annotation}


@router.delete("/{event_id}")
def archive_audit_event(event_id: uuid.UUID, context: RequestContext = Depends(get_context), db: Session = Depends(get_db)):
    require_role(context, "admin")
    entry = db.scalar(select(AuditLog).where(AuditLog.id == event_id, AuditLog.organization_id == context.organization_id))
    if entry is None:
        raise HTTPException(404, "审计记录不存在")
    if entry.action == "audit.archive":
        raise HTTPException(409, "删除留痕不可再次删除")
    existing = db.scalar(select(AuditLog).where(AuditLog.organization_id == context.organization_id, AuditLog.action == "audit.archive", AuditLog.entity_id == event_id))
    if existing is None:
        write_audit(db, organization_id=context.organization_id, actor_user_id=context.user_id, action="audit.archive", entity_type="audit", entity_id=event_id, after={"note": "从默认列表删除，原始记录保留"})
        db.commit()
    return {"id": str(event_id), "archived": True}

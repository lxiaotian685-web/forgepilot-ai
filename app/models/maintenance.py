from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import AuditMixin, SoftDeleteMixin, utcnow

ACTIVE_ONLY = text("deleted_at IS NULL")
JsonType = JSON().with_variant(JSONB(), "postgresql")


class Alert(AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index(
            "uq_alerts_organization_code_active",
            "organization_id",
            "code",
            unique=True,
            postgresql_where=ACTIVE_ONLY,
            sqlite_where=ACTIVE_ONLY,
        ),
        Index("ix_alerts_organization_status", "organization_id", "status"),
        Index("ix_alerts_device_id", "device_id"),
        CheckConstraint("level IN ('p1', 'p2', 'p3')", name="ck_alerts_level"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'acknowledged', 'closed')",
            name="ck_alerts_status",
        ),
        CheckConstraint(
            "source IN ('sensor', 'manual', 'model_inference')",
            name="ck_alerts_source",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default="sensor", server_default="sensor"
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acknowledged_by: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )


class Diagnosis(AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "diagnoses"
    __table_args__ = (
        Index(
            "uq_diagnoses_organization_code_active",
            "organization_id",
            "code",
            unique=True,
            postgresql_where=ACTIVE_ONLY,
            sqlite_where=ACTIVE_ONLY,
        ),
        Index("ix_diagnoses_device_id", "device_id"),
        CheckConstraint(
            "risk_level IN ('low', 'medium', 'high')", name="ck_diagnoses_risk_level"
        ),
        CheckConstraint(
            "status IN ('draft', 'confirmed', 'rejected')",
            name="ck_diagnoses_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="CASCADE"),
        nullable=False,
    )
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    conclusion: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(
        String(20), nullable=False, default="low", server_default="low"
    )
    confidence: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    evidence: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="draft", server_default="draft"
    )


class WorkOrder(AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "work_orders"
    __table_args__ = (
        Index(
            "uq_work_orders_organization_code_active",
            "organization_id",
            "code",
            unique=True,
            postgresql_where=ACTIVE_ONLY,
            sqlite_where=ACTIVE_ONLY,
        ),
        Index("ix_work_orders_organization_status", "organization_id", "status"),
        Index("ix_work_orders_device_id", "device_id"),
        Index("ix_work_orders_owner_user_id", "owner_user_id"),
        CheckConstraint(
            "priority IN ('p1', 'p2', 'p3', 'p4')", name="ck_work_orders_priority"
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'verifying', 'completed', "
            "'cancelled')",
            name="ck_work_orders_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("devices.id", ondelete="RESTRICT"),
        nullable=False,
    )
    alert_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True,
    )
    diagnosis_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("diagnoses.id", ondelete="SET NULL"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[str] = mapped_column(
        String(10), nullable=False, default="p3", server_default="p3"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", server_default="pending"
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index("ix_audit_logs_organization_created", "organization_id", "created_at"),
        Index("ix_audit_logs_entity", "entity_type", "entity_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), nullable=True
    )
    before: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    after: Mapped[dict | None] = mapped_column(JsonType, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

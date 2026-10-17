from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.base import AuditMixin, SoftDeleteMixin, utcnow

ACTIVE_ONLY = text("deleted_at IS NULL")


class Plant(AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "plants"
    __table_args__ = (
        Index(
            "uq_plants_organization_code_active",
            "organization_id",
            "code",
            unique=True,
            postgresql_where=ACTIVE_ONLY,
            sqlite_where=ACTIVE_ONLY,
        ),
        CheckConstraint(
            "status IN ('active', 'archived')", name="ck_plants_status"
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
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )


class Device(AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "devices"
    __table_args__ = (
        Index(
            "uq_devices_organization_code_active",
            "organization_id",
            "code",
            unique=True,
            postgresql_where=ACTIVE_ONLY,
            sqlite_where=ACTIVE_ONLY,
        ),
        Index("ix_devices_organization_state", "organization_id", "state"),
        Index("ix_devices_plant_id", "plant_id"),
        CheckConstraint(
            "state IN ('running', 'attention', 'alert', 'offline')",
            name="ck_devices_state",
        ),
        CheckConstraint("health >= 0 AND health <= 100", name="ck_devices_health"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("organizations.id", ondelete="RESTRICT"),
        nullable=False,
    )
    plant_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("plants.id", ondelete="SET NULL"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(120), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    health: Mapped[float] = mapped_column(
        Numeric(5, 2), nullable=False, default=100, server_default=text("100")
    )
    state: Mapped[str] = mapped_column(
        String(20), nullable=False, default="running", server_default="running"
    )


class DeviceComponent(AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "device_components"
    __table_args__ = (
        Index(
            "uq_device_components_device_code_active",
            "device_id",
            "code",
            unique=True,
            postgresql_where=ACTIVE_ONLY,
            sqlite_where=ACTIVE_ONLY,
        ),
        Index("ix_device_components_device_id", "device_id"),
        CheckConstraint(
            "status IN ('active', 'archived')", name="ck_device_components_status"
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
    parent_component_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("device_components.id", ondelete="CASCADE"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active"
    )


class DeviceParameter(AuditMixin, SoftDeleteMixin, Base):
    __tablename__ = "device_parameters"
    __table_args__ = (
        Index(
            "uq_device_parameters_device_name_recorded_active",
            "device_id",
            "name",
            "recorded_at",
            unique=True,
            postgresql_where=ACTIVE_ONLY,
            sqlite_where=ACTIVE_ONLY,
        ),
        Index(
            "ix_device_parameters_device_name_recorded",
            "device_id",
            "name",
            "recorded_at",
        ),
        CheckConstraint(
            "source IN ('nameplate', 'manual', 'sensor', 'imported', "
            "'model_inference', 'corrected')",
            name="ck_device_parameters_source",
        ),
        CheckConstraint(
            "source <> 'model_inference' OR is_authoritative = false",
            name="ck_device_parameters_inference_not_authoritative",
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
    component_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("device_components.id", ondelete="SET NULL"),
        nullable=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="sensor")
    source_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_authoritative: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )

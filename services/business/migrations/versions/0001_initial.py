"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

NOW = sa.text("now()")
ACTIVE_ONLY = sa.text("deleted_at IS NULL")


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
    ]


def _audit() -> list[sa.Column]:
    return _timestamps() + [
        sa.Column(
            "created_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "updated_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("code", sa.String(64), nullable=False, unique=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')", name="ck_organizations_status"
        ),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint(
            "status IN ('active', 'disabled')", name="ck_users_status"
        ),
    )

    op.create_table(
        "memberships",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False, server_default=sa.text("'viewer'")),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        *_timestamps(),
        sa.UniqueConstraint(
            "organization_id", "user_id", name="uq_memberships_organization_user"
        ),
        sa.CheckConstraint(
            "role IN ('owner', 'admin', 'manager', 'technician', 'viewer')",
            name="ck_memberships_role",
        ),
        sa.CheckConstraint(
            "status IN ('invited', 'active', 'disabled')",
            name="ck_memberships_status",
        ),
    )

    op.create_table(
        "plants",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        *_audit(),
        sa.CheckConstraint(
            "status IN ('active', 'archived')", name="ck_plants_status"
        ),
    )
    op.create_index(
        "uq_plants_organization_code_active",
        "plants",
        ["organization_id", "code"],
        unique=True,
        postgresql_where=ACTIVE_ONLY,
    )

    op.create_table(
        "devices",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "plant_id",
            sa.Uuid(),
            sa.ForeignKey("plants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("type", sa.String(120), nullable=True),
        sa.Column("model", sa.String(120), nullable=True),
        sa.Column("serial_number", sa.String(120), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column(
            "health",
            sa.Numeric(5, 2),
            nullable=False,
            server_default=sa.text("100"),
        ),
        sa.Column(
            "state",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'running'"),
        ),
        *_audit(),
        sa.CheckConstraint(
            "state IN ('running', 'attention', 'alert', 'offline')",
            name="ck_devices_state",
        ),
        sa.CheckConstraint(
            "health >= 0 AND health <= 100", name="ck_devices_health"
        ),
    )
    op.create_index(
        "uq_devices_organization_code_active",
        "devices",
        ["organization_id", "code"],
        unique=True,
        postgresql_where=ACTIVE_ONLY,
    )
    op.create_index(
        "ix_devices_organization_state", "devices", ["organization_id", "state"]
    )
    op.create_index("ix_devices_plant_id", "devices", ["plant_id"])

    op.create_table(
        "device_components",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.Uuid(),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_component_id",
            sa.Uuid(),
            sa.ForeignKey("device_components.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("position", sa.String(120), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        *_audit(),
        sa.CheckConstraint(
            "status IN ('active', 'archived')",
            name="ck_device_components_status",
        ),
    )
    op.create_index(
        "uq_device_components_device_code_active",
        "device_components",
        ["device_id", "code"],
        unique=True,
        postgresql_where=ACTIVE_ONLY,
    )
    op.create_index(
        "ix_device_components_device_id", "device_components", ["device_id"]
    )

    op.create_table(
        "device_parameters",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.Uuid(),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "component_id",
            sa.Uuid(),
            sa.ForeignKey("device_components.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("value", sa.Numeric(18, 6), nullable=False),
        sa.Column("unit", sa.String(32), nullable=True),
        sa.Column("source", sa.String(20), nullable=False),
        sa.Column("source_ref", sa.String(255), nullable=True),
        sa.Column(
            "is_authoritative",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), nullable=False
        ),
        *_audit(),
        sa.CheckConstraint(
            "source IN ('nameplate', 'manual', 'sensor', 'imported', "
            "'model_inference', 'corrected')",
            name="ck_device_parameters_source",
        ),
        sa.CheckConstraint(
            "source <> 'model_inference' OR is_authoritative = false",
            name="ck_device_parameters_inference_not_authoritative",
        ),
    )
    op.create_index(
        "uq_device_parameters_device_name_recorded_active",
        "device_parameters",
        ["device_id", "name", "recorded_at"],
        unique=True,
        postgresql_where=ACTIVE_ONLY,
    )
    op.create_index(
        "ix_device_parameters_device_name_recorded",
        "device_parameters",
        ["device_id", "name", "recorded_at"],
    )

    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.Uuid(),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'sensor'"),
        ),
        sa.Column(
            "occurred_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "acknowledged_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        *_audit(),
        sa.CheckConstraint(
            "level IN ('p1', 'p2', 'p3')", name="ck_alerts_level"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'acknowledged', 'closed')",
            name="ck_alerts_status",
        ),
        sa.CheckConstraint(
            "source IN ('sensor', 'manual', 'model_inference')",
            name="ck_alerts_source",
        ),
    )
    op.create_index(
        "uq_alerts_organization_code_active",
        "alerts",
        ["organization_id", "code"],
        unique=True,
        postgresql_where=ACTIVE_ONLY,
    )
    op.create_index(
        "ix_alerts_organization_status", "alerts", ["organization_id", "status"]
    )
    op.create_index("ix_alerts_device_id", "alerts", ["device_id"])

    op.create_table(
        "diagnoses",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.Uuid(),
            sa.ForeignKey("devices.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "alert_id",
            sa.Uuid(),
            sa.ForeignKey("alerts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("question", sa.Text(), nullable=True),
        sa.Column("conclusion", sa.Text(), nullable=True),
        sa.Column(
            "risk_level",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'low'"),
        ),
        sa.Column("confidence", sa.Numeric(5, 2), nullable=True),
        sa.Column("evidence", postgresql.JSONB(), nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'draft'"),
        ),
        *_audit(),
        sa.CheckConstraint(
            "risk_level IN ('low', 'medium', 'high')",
            name="ck_diagnoses_risk_level",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'confirmed', 'rejected')",
            name="ck_diagnoses_status",
        ),
    )
    op.create_index(
        "uq_diagnoses_organization_code_active",
        "diagnoses",
        ["organization_id", "code"],
        unique=True,
        postgresql_where=ACTIVE_ONLY,
    )
    op.create_index("ix_diagnoses_device_id", "diagnoses", ["device_id"])

    op.create_table(
        "work_orders",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "device_id",
            sa.Uuid(),
            sa.ForeignKey("devices.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "alert_id",
            sa.Uuid(),
            sa.ForeignKey("alerts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "diagnosis_id",
            sa.Uuid(),
            sa.ForeignKey("diagnoses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "priority",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'p3'"),
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "owner_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        *_audit(),
        sa.CheckConstraint(
            "priority IN ('p1', 'p2', 'p3', 'p4')",
            name="ck_work_orders_priority",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'verifying', 'completed', "
            "'cancelled')",
            name="ck_work_orders_status",
        ),
    )
    op.create_index(
        "uq_work_orders_organization_code_active",
        "work_orders",
        ["organization_id", "code"],
        unique=True,
        postgresql_where=ACTIVE_ONLY,
    )
    op.create_index(
        "ix_work_orders_organization_status",
        "work_orders",
        ["organization_id", "status"],
    )
    op.create_index("ix_work_orders_device_id", "work_orders", ["device_id"])
    op.create_index(
        "ix_work_orders_owner_user_id", "work_orders", ["owner_user_id"]
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Uuid(),
            sa.ForeignKey("organizations.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("before", postgresql.JSONB(), nullable=True),
        sa.Column("after", postgresql.JSONB(), nullable=True),
        sa.Column("ip", sa.String(64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=NOW,
        ),
    )
    op.create_index(
        "ix_audit_logs_organization_created",
        "audit_logs",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_audit_logs_entity", "audit_logs", ["entity_type", "entity_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_audit_logs_entity", table_name="audit_logs")
    op.drop_index(
        "ix_audit_logs_organization_created", table_name="audit_logs"
    )
    op.drop_table("audit_logs")

    op.drop_index("ix_work_orders_owner_user_id", table_name="work_orders")
    op.drop_index("ix_work_orders_device_id", table_name="work_orders")
    op.drop_index(
        "ix_work_orders_organization_status", table_name="work_orders"
    )
    op.drop_index(
        "uq_work_orders_organization_code_active", table_name="work_orders"
    )
    op.drop_table("work_orders")

    op.drop_index("ix_diagnoses_device_id", table_name="diagnoses")
    op.drop_index(
        "uq_diagnoses_organization_code_active", table_name="diagnoses"
    )
    op.drop_table("diagnoses")

    op.drop_index("ix_alerts_device_id", table_name="alerts")
    op.drop_index("ix_alerts_organization_status", table_name="alerts")
    op.drop_index("uq_alerts_organization_code_active", table_name="alerts")
    op.drop_table("alerts")

    op.drop_index(
        "ix_device_parameters_device_name_recorded",
        table_name="device_parameters",
    )
    op.drop_index(
        "uq_device_parameters_device_name_recorded_active",
        table_name="device_parameters",
    )
    op.drop_table("device_parameters")

    op.drop_index(
        "ix_device_components_device_id", table_name="device_components"
    )
    op.drop_index(
        "uq_device_components_device_code_active",
        table_name="device_components",
    )
    op.drop_table("device_components")

    op.drop_index("ix_devices_plant_id", table_name="devices")
    op.drop_index("ix_devices_organization_state", table_name="devices")
    op.drop_index("uq_devices_organization_code_active", table_name="devices")
    op.drop_table("devices")

    op.drop_index(
        "uq_plants_organization_code_active", table_name="plants"
    )
    op.drop_table("plants")

    op.drop_table("memberships")
    op.drop_table("users")
    op.drop_table("organizations")

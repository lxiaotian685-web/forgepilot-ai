"""maintenance records (device history)

Revision ID: 0003_maintenance_records
Revises: 0002_diagnosis_confirmation
Create Date: 2026-10-21
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_maintenance_records"
down_revision: str | None = "0002_diagnosis_confirmation"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

NOW = sa.text("now()")
WORK_ORDER_ACTIVE = sa.text(
    "work_order_id IS NOT NULL AND deleted_at IS NULL"
)


def upgrade() -> None:
    op.create_table(
        "maintenance_records",
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
            "work_order_id",
            sa.Uuid(),
            sa.ForeignKey("work_orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "diagnosis_id",
            sa.Uuid(),
            sa.ForeignKey("diagnoses.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "alert_id",
            sa.Uuid(),
            sa.ForeignKey("alerts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "record_type",
            sa.String(20),
            nullable=False,
            server_default=sa.text("'maintenance'"),
        ),
        sa.Column("summary", sa.String(255), nullable=False),
        sa.Column("root_cause", sa.Text(), nullable=True),
        sa.Column("action_taken", sa.Text(), nullable=True),
        sa.Column(
            "recorded_by",
            sa.Uuid(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "recorded_at", sa.DateTime(timezone=True), nullable=False
        ),
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
        sa.CheckConstraint(
            "record_type IN ('maintenance', 'inspection', 'repair', "
            "'replacement', 'other')",
            name="ck_maintenance_records_type",
        ),
    )
    op.create_index(
        "ix_maintenance_records_org_device_recorded",
        "maintenance_records",
        ["organization_id", "device_id", "recorded_at"],
    )
    op.create_index(
        "uq_maintenance_records_work_order_active",
        "maintenance_records",
        ["work_order_id"],
        unique=True,
        postgresql_where=WORK_ORDER_ACTIVE,
    )
    op.create_index(
        "ix_maintenance_records_work_order_id",
        "maintenance_records",
        ["work_order_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_maintenance_records_work_order_id",
        table_name="maintenance_records",
    )
    op.drop_index(
        "uq_maintenance_records_work_order_active",
        table_name="maintenance_records",
    )
    op.drop_index(
        "ix_maintenance_records_org_device_recorded",
        table_name="maintenance_records",
    )
    op.drop_table("maintenance_records")

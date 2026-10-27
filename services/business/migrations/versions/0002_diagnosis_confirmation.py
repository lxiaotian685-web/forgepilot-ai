"""diagnosis confirmation and work order link

Revision ID: 0002_diagnosis_confirmation
Revises: 0001_initial
Create Date: 2026-10-17
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_diagnosis_confirmation"
down_revision: str | None = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "diagnoses",
        sa.Column("model_source", sa.String(120), nullable=True),
    )
    op.add_column(
        "diagnoses",
        sa.Column("confirmed_by", sa.Uuid(), nullable=True),
    )
    op.create_foreign_key(
        "fk_diagnoses_confirmed_by",
        "diagnoses",
        "users",
        ["confirmed_by"],
        ["id"],
        ondelete="SET NULL",
    )
    op.add_column(
        "diagnoses",
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "uq_work_orders_diagnosis_active",
        "work_orders",
        ["diagnosis_id"],
        unique=True,
        postgresql_where=sa.text(
            "diagnosis_id IS NOT NULL AND deleted_at IS NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_work_orders_diagnosis_active", table_name="work_orders"
    )
    op.drop_constraint(
        "fk_diagnoses_confirmed_by", "diagnoses", type_="foreignkey"
    )
    op.drop_column("diagnoses", "confirmed_at")
    op.drop_column("diagnoses", "confirmed_by")
    op.drop_column("diagnoses", "model_source")

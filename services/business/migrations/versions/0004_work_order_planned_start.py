"""Add planned start time for work order schedule ranges.

Revision ID: 0004_work_order_planned_start
Revises: 0003_maintenance_records
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_work_order_planned_start"
down_revision: str | None = "0003_maintenance_records"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "work_orders",
        sa.Column("planned_start_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("work_orders", "planned_start_at")

"""add receipt group id to stock movements

Revision ID: e7c1b9a2f4d0
Revises: d2b8f3c4a1e9
Create Date: 2026-04-20 22:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import uuid


revision: str = "e7c1b9a2f4d0"
down_revision: Union[str, Sequence[str], None] = "d2b8f3c4a1e9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("stock_movements", sa.Column("receipt_group_id", sa.UUID(), nullable=True))

    connection = op.get_bind()
    movements = connection.execute(
        sa.text(
            """
            SELECT id, store_id, supplier_reference, document_reference, reason
            FROM stock_movements
            WHERE movement_type = 'entry'
            """
        )
    ).fetchall()

    grouped_ids: dict[tuple[str, str, str, str], str] = {}
    for movement in movements:
        key = (
            str(movement.store_id),
            movement.supplier_reference or "",
            movement.document_reference or "",
            movement.reason or "",
        )
        grouped_ids.setdefault(key, str(uuid.uuid4()))
        connection.execute(
            sa.text("UPDATE stock_movements SET receipt_group_id = :group_id WHERE id = :movement_id"),
            {"group_id": grouped_ids[key], "movement_id": movement.id},
        )


def downgrade() -> None:
    op.drop_column("stock_movements", "receipt_group_id")

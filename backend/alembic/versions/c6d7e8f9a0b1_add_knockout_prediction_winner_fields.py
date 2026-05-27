"""Add knockout prediction winner fields

Revision ID: c6d7e8f9a0b1
Revises: b1c2d3e4f5a6
Create Date: 2026-05-27 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "c6d7e8f9a0b1"
down_revision = "b1c2d3e4f5a6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("predictions") as batch_op:
        batch_op.add_column(sa.Column("knockout_winner_side", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("knockout_resolution", sa.String(), nullable=True))


def downgrade():
    with op.batch_alter_table("predictions") as batch_op:
        batch_op.drop_column("knockout_resolution")
        batch_op.drop_column("knockout_winner_side")

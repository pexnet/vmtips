"""Add release auth fields and the extra-question lock.

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-07 13:45:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.add_column(
            sa.Column("display_name_lower", sa.String(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("last_login_at", sa.DateTime(), nullable=True)
        )

    op.execute(
        "UPDATE users "
        "SET display_name_lower = lower(trim(display_name))"
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column(
            "display_name_lower",
            existing_type=sa.String(),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            "uq_users_display_name_lower",
            ["display_name_lower"],
        )

    with op.batch_alter_table("tournament_phases") as batch_op:
        batch_op.add_column(
            sa.Column("extra_questions_lock_at", sa.DateTime(), nullable=True)
        )

    with op.batch_alter_table("league_bonus_questions") as batch_op:
        batch_op.add_column(
            sa.Column("closed_at", sa.DateTime(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("league_bonus_questions") as batch_op:
        batch_op.drop_column("closed_at")

    with op.batch_alter_table("tournament_phases") as batch_op:
        batch_op.drop_column("extra_questions_lock_at")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint(
            "uq_users_display_name_lower",
            type_="unique",
        )
        batch_op.drop_column("display_name_lower")
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("is_active")

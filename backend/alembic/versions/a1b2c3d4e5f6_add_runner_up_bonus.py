"""Add runner-up tournament bonus fields.

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-06-07 20:30:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def _has_column(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    rows = bind.execute(sa.text(f"PRAGMA table_info({table_name})")).mappings().all()
    return any(row["name"] == column_name for row in rows)


def upgrade() -> None:
    if not _has_column("tournament_bonuses", "runner_up_team_id"):
        with op.batch_alter_table("tournament_bonuses") as batch_op:
            batch_op.add_column(sa.Column("runner_up_team_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_tournament_bonuses_runner_up_team_id_teams",
                "teams",
                ["runner_up_team_id"],
                ["id"],
            )

    if not _has_column("tournament_results", "runner_up_team_id"):
        with op.batch_alter_table("tournament_results") as batch_op:
            batch_op.add_column(sa.Column("runner_up_team_id", sa.Integer(), nullable=True))
            batch_op.create_foreign_key(
                "fk_tournament_results_runner_up_team_id_teams",
                "teams",
                ["runner_up_team_id"],
                ["id"],
            )


def downgrade() -> None:
    if _has_column("tournament_results", "runner_up_team_id"):
        with op.batch_alter_table("tournament_results") as batch_op:
            batch_op.drop_constraint(
                "fk_tournament_results_runner_up_team_id_teams",
                type_="foreignkey",
            )
            batch_op.drop_column("runner_up_team_id")

    if _has_column("tournament_bonuses", "runner_up_team_id"):
        with op.batch_alter_table("tournament_bonuses") as batch_op:
            batch_op.drop_constraint(
                "fk_tournament_bonuses_runner_up_team_id_teams",
                type_="foreignkey",
            )
            batch_op.drop_column("runner_up_team_id")

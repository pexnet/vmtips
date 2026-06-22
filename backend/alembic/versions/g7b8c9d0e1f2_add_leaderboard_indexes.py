"""Add leaderboard performance indexes

Revision ID: g7b8c9d0e1f2
Revises: a1b2c3d4e5f6
Create Date: 2026-06-22

Composite indexes on the hot leaderboard query paths:
- predictions (league_id, match_id) and (user_id, league_id)
- matches (status, match_date)
- bracket_predictions (league_id, user_id)
- tournament_bonuses (league_id, user_id)
- league_members (league_id)
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "g7b8c9d0e1f2"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotent: use IF NOT EXISTS so re-running on a DB that already
    # has these indexes (e.g. from create_all) doesn't fail.
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_predictions_league_match "
        "ON predictions (league_id, match_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_predictions_user_league "
        "ON predictions (user_id, league_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_matches_status_date "
        "ON matches (status, match_date)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_bracket_predictions_league_user "
        "ON bracket_predictions (league_id, user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_tournament_bonuses_league_user "
        "ON tournament_bonuses (league_id, user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_league_members_league "
        "ON league_members (league_id)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_league_members_league")
    op.execute("DROP INDEX IF EXISTS ix_tournament_bonuses_league_user")
    op.execute("DROP INDEX IF EXISTS ix_bracket_predictions_league_user")
    op.execute("DROP INDEX IF EXISTS ix_matches_status_date")
    op.execute("DROP INDEX IF EXISTS ix_predictions_user_league")
    op.execute("DROP INDEX IF EXISTS ix_predictions_league_match")
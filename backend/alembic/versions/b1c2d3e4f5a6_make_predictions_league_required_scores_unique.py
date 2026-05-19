"""Make prediction league required and score cache league-unique

Revision ID: b1c2d3e4f5a6
Revises: 8a9b12c3d4e5
Create Date: 2026-05-19 21:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "b1c2d3e4f5a6"
down_revision = "8a9b12c3d4e5"
branch_labels = None
depends_on = None


def _default_league_id(conn) -> int:
    league_id = conn.execute(
        sa.text("SELECT id FROM leagues WHERE name = 'VM2026' ORDER BY id LIMIT 1")
    ).scalar()
    if league_id is None:
        league_id = conn.execute(sa.text("SELECT id FROM leagues ORDER BY id LIMIT 1")).scalar()
    return int(league_id or 1)


def upgrade():
    conn = op.get_bind()
    default_league_id = _default_league_id(conn)
    conn.execute(
        sa.text("UPDATE predictions SET league_id = :league_id WHERE league_id IS NULL"),
        {"league_id": default_league_id},
    )

    if conn.dialect.name == "sqlite":
        conn.execute(sa.text("""
            CREATE TABLE predictions_new (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                league_id INTEGER NOT NULL DEFAULT 1,
                match_id INTEGER NOT NULL,
                home_goals INTEGER NOT NULL,
                away_goals INTEGER NOT NULL,
                created_at DATETIME,
                updated_at DATETIME,
                UNIQUE(user_id, match_id, league_id)
            )
        """))
        conn.execute(sa.text("""
            INSERT INTO predictions_new (id, user_id, league_id, match_id, home_goals, away_goals, created_at, updated_at)
            SELECT id, user_id, league_id, match_id, home_goals, away_goals, created_at, updated_at
            FROM predictions
        """))
        conn.execute(sa.text("DROP TABLE predictions"))
        conn.execute(sa.text("ALTER TABLE predictions_new RENAME TO predictions"))
        conn.execute(sa.text("CREATE INDEX ix_predictions_id ON predictions (id)"))

        conn.execute(sa.text("""
            CREATE TABLE scores_new (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                league_id INTEGER,
                match_points INTEGER,
                bracket_points INTEGER,
                tournament_bonus_points INTEGER,
                league_bonus_points INTEGER,
                total_points INTEGER,
                updated_at DATETIME,
                UNIQUE(user_id, league_id)
            )
        """))
        conn.execute(sa.text("""
            INSERT INTO scores_new (id, user_id, league_id, match_points, bracket_points,
                tournament_bonus_points, league_bonus_points, total_points, updated_at)
            SELECT id, user_id, league_id, match_points, bracket_points,
                tournament_bonus_points, league_bonus_points, total_points, updated_at
            FROM scores
        """))
        conn.execute(sa.text("DROP TABLE scores"))
        conn.execute(sa.text("ALTER TABLE scores_new RENAME TO scores"))
        conn.execute(sa.text("CREATE INDEX ix_scores_id ON scores (id)"))
    else:
        with op.batch_alter_table("predictions") as batch_op:
            batch_op.alter_column(
                "league_id",
                existing_type=sa.Integer(),
                nullable=False,
                server_default="1",
            )
        op.create_unique_constraint("uq_score_user_league", "scores", ["user_id", "league_id"])


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name == "sqlite":
        conn.execute(sa.text("""
            CREATE TABLE predictions_old (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                league_id INTEGER,
                match_id INTEGER NOT NULL,
                home_goals INTEGER NOT NULL,
                away_goals INTEGER NOT NULL,
                created_at DATETIME,
                updated_at DATETIME,
                UNIQUE(user_id, match_id, league_id)
            )
        """))
        conn.execute(sa.text("""
            INSERT INTO predictions_old (id, user_id, league_id, match_id, home_goals, away_goals, created_at, updated_at)
            SELECT id, user_id, league_id, match_id, home_goals, away_goals, created_at, updated_at
            FROM predictions
        """))
        conn.execute(sa.text("DROP TABLE predictions"))
        conn.execute(sa.text("ALTER TABLE predictions_old RENAME TO predictions"))
        conn.execute(sa.text("CREATE INDEX ix_predictions_id ON predictions (id)"))
    else:
        op.drop_constraint("uq_score_user_league", "scores", type_="unique")
        with op.batch_alter_table("predictions") as batch_op:
            batch_op.alter_column("league_id", existing_type=sa.Integer(), nullable=True)

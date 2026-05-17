"""Add league_id to predictions, tournament_bonuses, bracket_predictions

Revision ID: 8a9b12c3d4e5
Revises: 635ab6ee45fb
Create Date: 2025-05-17 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8a9b12c3d4e5'
down_revision = '635ab6ee45fb'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    dialect = conn.dialect.name
    is_sqlite = dialect == 'sqlite'

    # ── predictions ──
    with op.batch_alter_table('predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('league_id', sa.Integer(), nullable=True))
    if not is_sqlite:
        op.create_foreign_key('fk_predictions_league_id', 'predictions', 'leagues', ['league_id'], ['id'])
    # SQLite: recreate table to add unique constraint including league_id
    if is_sqlite:
        conn.execute(sa.text("""
            CREATE TABLE predictions_new (
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
            INSERT INTO predictions_new (id, user_id, league_id, match_id, home_goals, away_goals, created_at, updated_at)
            SELECT id, user_id, NULL, match_id, home_goals, away_goals, created_at, updated_at FROM predictions
        """))
        conn.execute(sa.text("DROP TABLE predictions"))
        conn.execute(sa.text("ALTER TABLE predictions_new RENAME TO predictions"))
        conn.execute(sa.text("CREATE INDEX ix_predictions_id ON predictions (id)"))
    else:
        op.drop_constraint('uq_user_match_prediction', 'predictions', type_='unique')
        op.create_unique_constraint('uq_user_match_league_prediction', 'predictions', ['user_id', 'match_id', 'league_id'])
        op.create_foreign_key('fk_predictions_league_id', 'predictions', 'leagues', ['league_id'], ['id'])

    # ── tournament_bonuses ──
    with op.batch_alter_table('tournament_bonuses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('league_id', sa.Integer(), nullable=True))
    if is_sqlite:
        conn.execute(sa.text("""
            CREATE TABLE tournament_bonuses_new (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                league_id INTEGER,
                winner_team_id INTEGER,
                top_scorer_name VARCHAR,
                bronze_winner_team_id INTEGER,
                most_goals_team_id INTEGER,
                most_conceded_team_id INTEGER,
                custom_bonus_1 VARCHAR,
                custom_bonus_2 VARCHAR,
                created_at DATETIME,
                updated_at DATETIME,
                UNIQUE(user_id, league_id)
            )
        """))
        conn.execute(sa.text("""
            INSERT INTO tournament_bonuses_new (id, user_id, league_id, winner_team_id, top_scorer_name,
                bronze_winner_team_id, most_goals_team_id, most_conceded_team_id,
                custom_bonus_1, custom_bonus_2, created_at, updated_at)
            SELECT id, user_id, NULL, winner_team_id, top_scorer_name,
                bronze_winner_team_id, most_goals_team_id, most_conceded_team_id,
                custom_bonus_1, custom_bonus_2, created_at, updated_at
            FROM tournament_bonuses
        """))
        conn.execute(sa.text("DROP TABLE tournament_bonuses"))
        conn.execute(sa.text("ALTER TABLE tournament_bonuses_new RENAME TO tournament_bonuses"))
        conn.execute(sa.text("CREATE INDEX ix_tournament_bonuses_id ON tournament_bonuses (id)"))
    else:
        op.drop_constraint('uq_user_league_bonus', 'tournament_bonuses', type_='unique')
        op.create_unique_constraint('uq_user_league_bonus', 'tournament_bonuses', ['user_id', 'league_id'])
        op.create_foreign_key('fk_tournament_bonuses_league_id', 'tournament_bonuses', 'leagues', ['league_id'], ['id'])

    # ── bracket_predictions ──
    with op.batch_alter_table('bracket_predictions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('league_id', sa.Integer(), nullable=True))
    if is_sqlite:
        conn.execute(sa.text("""
            CREATE TABLE bracket_predictions_new (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                league_id INTEGER,
                team_id INTEGER NOT NULL,
                round VARCHAR NOT NULL,
                source VARCHAR DEFAULT 'knockout_prediction',
                created_at DATETIME,
                updated_at DATETIME,
                UNIQUE(user_id, league_id, team_id, round)
            )
        """))
        conn.execute(sa.text("""
            INSERT INTO bracket_predictions_new (id, user_id, league_id, team_id, round, source, created_at, updated_at)
            SELECT id, user_id, NULL, team_id, round, source, created_at, updated_at FROM bracket_predictions
        """))
        conn.execute(sa.text("DROP TABLE bracket_predictions"))
        conn.execute(sa.text("ALTER TABLE bracket_predictions_new RENAME TO bracket_predictions"))
        conn.execute(sa.text("CREATE INDEX ix_bracket_predictions_id ON bracket_predictions (id)"))
    else:
        op.drop_constraint('uq_user_team_round', 'bracket_predictions', type_='unique')
        op.create_unique_constraint('uq_user_league_team_round', 'bracket_predictions', ['user_id', 'league_id', 'team_id', 'round'])
        op.create_foreign_key('fk_bracket_predictions_league_id', 'bracket_predictions', 'leagues', ['league_id'], ['id'])


def downgrade():
    pass

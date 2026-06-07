"""add_bracket_advancement_phase_standings_bonus_fields

Revision ID: 635ab6ee45fb
Revises: 7e52b57de43e
Create Date: 2026-05-16 20:12:01.902413

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '635ab6ee45fb'
down_revision: Union[str, Sequence[str], None] = '7e52b57de43e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # ── New tables (may already exist from create_all) ──────────────
    existing = set(conn.execute(sa.text(
        "SELECT name FROM sqlite_master WHERE type='table'"
    )).scalars())

    if 'knockout_advancements' not in existing:
        op.create_table(
            'knockout_advancements',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('team_id', sa.Integer(), nullable=False),
            sa.Column('round', sa.String(), nullable=False),
            sa.Column('match_number', sa.Integer(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('team_id', 'round', name='uq_team_round_advancement'),
        )

    if 'tournament_phases' not in existing:
        op.create_table(
            'tournament_phases',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('phase', sa.String(), nullable=True),
            sa.Column('group_deadline', sa.DateTime(), nullable=True),
            sa.Column('knockout_opens_at', sa.DateTime(), nullable=True),
            sa.Column('knockout_deadline', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.execute("INSERT INTO tournament_phases (phase) VALUES ('group_open')")

    if 'group_standings' not in existing:
        op.create_table(
            'group_standings',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('team_id', sa.Integer(), nullable=False),
            sa.Column('group', sa.String(1), nullable=False),
            sa.Column('position', sa.Integer(), nullable=True),
            sa.Column('played', sa.Integer(), nullable=True),
            sa.Column('won', sa.Integer(), nullable=True),
            sa.Column('drawn', sa.Integer(), nullable=True),
            sa.Column('lost', sa.Integer(), nullable=True),
            sa.Column('goals_for', sa.Integer(), nullable=True),
            sa.Column('goals_against', sa.Integer(), nullable=True),
            sa.Column('goal_difference', sa.Integer(), nullable=True),
            sa.Column('points', sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
            sa.PrimaryKeyConstraint('id'),
        )

    if 'sync_config' not in existing:
        op.create_table(
            'sync_config',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('source', sa.String(), nullable=False),
            sa.Column('auto_sync_enabled', sa.Boolean(), nullable=True),
            sa.Column('auto_sync_interval_minutes', sa.Integer(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint('id'),
        )
        op.execute(
            "INSERT INTO sync_config (source, auto_sync_enabled, auto_sync_interval_minutes) "
            "VALUES ('worldcupjson', 0, 5)"
        )

    if 'bracket_predictions' not in existing:
        op.create_table(
            'bracket_predictions',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', sa.Integer(), nullable=False),
            sa.Column('team_id', sa.Integer(), nullable=False),
            sa.Column('round', sa.String(), nullable=False),
            sa.Column('source', sa.String(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
            sa.ForeignKeyConstraint(['user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'team_id', 'round', name='uq_user_team_round'),
        )
        with op.batch_alter_table('bracket_predictions', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_bracket_predictions_id'), ['id'], unique=False)
        existing.add('bracket_predictions')

    if 'tournament_results' not in existing:
        op.create_table(
            'tournament_results',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('winner_team_id', sa.Integer(), nullable=True),
            sa.Column('top_scorer_name', sa.String(), nullable=True),
            sa.Column('bronze_winner_team_id', sa.Integer(), nullable=True),
            sa.Column('most_goals_team_id', sa.Integer(), nullable=True),
            sa.Column('most_conceded_team_id', sa.Integer(), nullable=True),
            sa.Column('custom_bonus_1_answer', sa.String(), nullable=True),
            sa.Column('custom_bonus_2_answer', sa.String(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['bronze_winner_team_id'], ['teams.id']),
            sa.ForeignKeyConstraint(['most_conceded_team_id'], ['teams.id']),
            sa.ForeignKeyConstraint(['most_goals_team_id'], ['teams.id']),
            sa.ForeignKeyConstraint(['winner_team_id'], ['teams.id']),
            sa.PrimaryKeyConstraint('id'),
        )
        with op.batch_alter_table('tournament_results', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_tournament_results_id'), ['id'], unique=False)
        existing.add('tournament_results')

    # ── Alter existing tables ───────────────────────────────────────
    # bracket_predictions: add source column
    bp_cols = {row[1] for row in conn.execute(sa.text(
        "PRAGMA table_info(bracket_predictions)"
    )).fetchall()}
    if 'source' not in bp_cols:
        with op.batch_alter_table('bracket_predictions', schema=None) as batch_op:
            batch_op.add_column(sa.Column('source', sa.String(), nullable=True))

    # tournament_bonuses: add/remove columns
    tb_cols = {row[1] for row in conn.execute(sa.text(
        "PRAGMA table_info(tournament_bonuses)"
    )).fetchall()}
    with op.batch_alter_table('tournament_bonuses', schema=None) as batch_op:
        if 'bronze_winner_team_id' not in tb_cols:
            batch_op.add_column(sa.Column('bronze_winner_team_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_tournament_bonuses_bronze_winner', 'teams', ['bronze_winner_team_id'], ['id'])
        if 'most_goals_team_id' not in tb_cols:
            batch_op.add_column(sa.Column('most_goals_team_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_tournament_bonuses_most_goals', 'teams', ['most_goals_team_id'], ['id'])
        if 'most_conceded_team_id' not in tb_cols:
            batch_op.add_column(sa.Column('most_conceded_team_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_tournament_bonuses_most_conceded', 'teams', ['most_conceded_team_id'], ['id'])
        if 'custom_bonus_1' not in tb_cols:
            batch_op.add_column(sa.Column('custom_bonus_1', sa.String(), nullable=True))
        if 'custom_bonus_2' not in tb_cols:
            batch_op.add_column(sa.Column('custom_bonus_2', sa.String(), nullable=True))
        if 'top_assist_name' in tb_cols:
            batch_op.drop_column('top_assist_name')
        if 'total_goals' in tb_cols:
            batch_op.drop_column('total_goals')

    # tournament_results: add/remove columns
    tr_cols = {row[1] for row in conn.execute(sa.text(
        "PRAGMA table_info(tournament_results)"
    )).fetchall()}
    with op.batch_alter_table('tournament_results', schema=None) as batch_op:
        if 'bronze_winner_team_id' not in tr_cols:
            batch_op.add_column(sa.Column('bronze_winner_team_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_tournament_results_bronze_winner', 'teams', ['bronze_winner_team_id'], ['id'])
        if 'most_goals_team_id' not in tr_cols:
            batch_op.add_column(sa.Column('most_goals_team_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_tournament_results_most_goals', 'teams', ['most_goals_team_id'], ['id'])
        if 'most_conceded_team_id' not in tr_cols:
            batch_op.add_column(sa.Column('most_conceded_team_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key('fk_tournament_results_most_conceded', 'teams', ['most_conceded_team_id'], ['id'])
        if 'custom_bonus_1_answer' not in tr_cols:
            batch_op.add_column(sa.Column('custom_bonus_1_answer', sa.String(), nullable=True))
        if 'custom_bonus_2_answer' not in tr_cols:
            batch_op.add_column(sa.Column('custom_bonus_2_answer', sa.String(), nullable=True))
        if 'top_assist_name' in tr_cols:
            batch_op.drop_column('top_assist_name')
        if 'total_goals' in tr_cols:
            batch_op.drop_column('total_goals')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('group_standings')
    op.drop_table('sync_config')
    op.drop_table('tournament_phases')
    op.drop_table('knockout_advancements')

    with op.batch_alter_table('tournament_results', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_goals', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('top_assist_name', sa.VARCHAR(), nullable=True))
        batch_op.drop_constraint('fk_tournament_results_most_goals', type_='foreignkey')
        batch_op.drop_constraint('fk_tournament_results_bronze_winner', type_='foreignkey')
        batch_op.drop_constraint('fk_tournament_results_most_conceded', type_='foreignkey')
        batch_op.drop_column('custom_bonus_2_answer')
        batch_op.drop_column('custom_bonus_1_answer')
        batch_op.drop_column('most_conceded_team_id')
        batch_op.drop_column('most_goals_team_id')
        batch_op.drop_column('bronze_winner_team_id')

    with op.batch_alter_table('tournament_bonuses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('total_goals', sa.INTEGER(), nullable=True))
        batch_op.add_column(sa.Column('top_assist_name', sa.VARCHAR(), nullable=True))
        batch_op.drop_constraint('fk_tournament_bonuses_bronze_winner', type_='foreignkey')
        batch_op.drop_constraint('fk_tournament_bonuses_most_goals', type_='foreignkey')
        batch_op.drop_constraint('fk_tournament_bonuses_most_conceded', type_='foreignkey')
        batch_op.drop_column('custom_bonus_2')
        batch_op.drop_column('custom_bonus_1')
        batch_op.drop_column('most_conceded_team_id')
        batch_op.drop_column('most_goals_team_id')
        batch_op.drop_column('bronze_winner_team_id')

    with op.batch_alter_table('bracket_predictions', schema=None) as batch_op:
        batch_op.drop_column('source')

"""
Ensure unique index for saas_registros_operacionais.id_evento exists

Revision ID: cd34ef56ab78
Revises: bcd34ef56a78
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'cd34ef56ab78'
down_revision = 'bcd34ef56a78'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def has_index(table_name: str, index_name: str) -> bool:
        try:
            return any(i.get('name') == index_name for i in insp.get_indexes(table_name))
        except Exception:
            return False

    # If unique index missing, (re)create it
    if not has_index('saas_registros_operacionais', 'ix_saas_operacionais_id_evento'):
        op.create_index('ix_saas_operacionais_id_evento', 'saas_registros_operacionais', ['id_evento'], unique=True)


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def has_index(table_name: str, index_name: str) -> bool:
        try:
            return any(i.get('name') == index_name for i in insp.get_indexes(table_name))
        except Exception:
            return False

    if has_index('saas_registros_operacionais', 'ix_saas_operacionais_id_evento'):
        op.drop_index('ix_saas_operacionais_id_evento', table_name='saas_registros_operacionais')
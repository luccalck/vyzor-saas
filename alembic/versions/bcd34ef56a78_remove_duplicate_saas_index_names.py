"""
Remove duplicate SAAS index names created outside Alembic

Revision ID: bcd34ef56a78
Revises: ab12cd34ef56
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'bcd34ef56a78'
down_revision = 'ab12cd34ef56'
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

    # Drop duplicate indexes that mirror Alembic-managed ones
    duplicates = [
        ('saas_registros_financeiros', 'ix_saas_registros_financeiros_id_transacao'),
        ('saas_registros_operacionais', 'ix_saas_registros_operacionais_id_evento'),
        ('saas_registros_produtos', 'ix_saas_registros_produtos_id_venda'),
        ('saas_registros_produtos', 'ix_saas_registros_produtos_sku_produto'),
    ]
    for table, index in duplicates:
        if has_index(table, index):
            op.drop_index(index, table_name=table)


def downgrade():
    # Recreate duplicates in case of downgrade (non-unique mirrors)
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def has_index(table_name: str, index_name: str) -> bool:
        try:
            return any(i.get('name') == index_name for i in insp.get_indexes(table_name))
        except Exception:
            return False

    if not has_index('saas_registros_financeiros', 'ix_saas_registros_financeiros_id_transacao'):
        op.create_index('ix_saas_registros_financeiros_id_transacao', 'saas_registros_financeiros', ['id_transacao'], unique=True)
    if not has_index('saas_registros_operacionais', 'ix_saas_registros_operacionais_id_evento'):
        op.create_index('ix_saas_registros_operacionais_id_evento', 'saas_registros_operacionais', ['id_evento'], unique=True)
    if not has_index('saas_registros_produtos', 'ix_saas_registros_produtos_id_venda'):
        op.create_index('ix_saas_registros_produtos_id_venda', 'saas_registros_produtos', ['id_venda'], unique=False)
    if not has_index('saas_registros_produtos', 'ix_saas_registros_produtos_sku_produto'):
        op.create_index('ix_saas_registros_produtos_sku_produto', 'saas_registros_produtos', ['sku_produto'], unique=False)
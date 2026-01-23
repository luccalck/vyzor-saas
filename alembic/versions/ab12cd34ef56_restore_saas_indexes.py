"""
Restore SAAS indexes for id_transacao, id_evento, id_venda, sku_produto

Revision ID: ab12cd34ef56
Revises: f1c2d3e4f5a6
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'ab12cd34ef56'
down_revision = 'f1c2d3e4f5a6'
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

    # Financeiros: unique id_transacao
    if not has_index('saas_registros_financeiros', 'ix_saas_financeiros_id_transacao'):
        op.create_index('ix_saas_financeiros_id_transacao', 'saas_registros_financeiros', ['id_transacao'], unique=True)

    # Operacionais: unique id_evento
    if not has_index('saas_registros_operacionais', 'ix_saas_operacionais_id_evento'):
        op.create_index('ix_saas_operacionais_id_evento', 'saas_registros_operacionais', ['id_evento'], unique=True)

    # Produtos: non-unique id_venda e sku_produto
    if not has_index('saas_registros_produtos', 'ix_saas_produtos_id_venda'):
        op.create_index('ix_saas_produtos_id_venda', 'saas_registros_produtos', ['id_venda'], unique=False)
    if not has_index('saas_registros_produtos', 'ix_saas_produtos_sku_produto'):
        op.create_index('ix_saas_produtos_sku_produto', 'saas_registros_produtos', ['sku_produto'], unique=False)


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def has_index(table_name: str, index_name: str) -> bool:
        try:
            return any(i.get('name') == index_name for i in insp.get_indexes(table_name))
        except Exception:
            return False

    if has_index('saas_registros_financeiros', 'ix_saas_financeiros_id_transacao'):
        op.drop_index('ix_saas_financeiros_id_transacao', table_name='saas_registros_financeiros')
    if has_index('saas_registros_operacionais', 'ix_saas_operacionais_id_evento'):
        op.drop_index('ix_saas_operacionais_id_evento', table_name='saas_registros_operacionais')
    if has_index('saas_registros_produtos', 'ix_saas_produtos_id_venda'):
        op.drop_index('ix_saas_produtos_id_venda', table_name='saas_registros_produtos')
    if has_index('saas_registros_produtos', 'ix_saas_produtos_sku_produto'):
        op.drop_index('ix_saas_produtos_sku_produto', table_name='saas_registros_produtos')
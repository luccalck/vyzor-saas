"""Cleanup and optimize DB: drop TesteValor, add indexes

Revision ID: f1c2d3e4f5a6
Revises: e1a2b3c4d5e6
Create Date: 2025-10-19
"""
from alembic import op
import sqlalchemy as sa

revision = 'f1c2d3e4f5a6'
down_revision = '763fc9ad8e11'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # Drop TesteValor if exists
    if insp.has_table('TesteValor'):
        op.drop_table('TesteValor')

    # Helper to check index existence by name
    def has_index(table_name: str, index_name: str) -> bool:
        try:
            idxs = insp.get_indexes(table_name)
            return any(i.get('name') == index_name for i in idxs)
        except Exception:
            return False

    # usuarios: index on email (non-unique for now)
    if not has_index('usuarios', 'ix_usuarios_email'):
        op.create_index('ix_usuarios_email', 'usuarios', ['email'], unique=False)

    # usuarios: index on departamento_id
    if not has_index('usuarios', 'ix_usuarios_departamento_id'):
        op.create_index('ix_usuarios_departamento_id', 'usuarios', ['departamento_id'], unique=False)

    # atividades_usuarios: index on usuario_id
    if not has_index('atividades_usuarios', 'ix_atividades_usuarios_usuario_id'):
        op.create_index('ix_atividades_usuarios_usuario_id', 'atividades_usuarios', ['usuario_id'], unique=False)

    # logs_importacoes: index on importacao_id
    if not has_index('logs_importacoes', 'ix_logs_importacoes_importacao_id'):
        op.create_index('ix_logs_importacoes_importacao_id', 'logs_importacoes', ['importacao_id'], unique=False)

    # registros_importados: index on importacao_id
    if not has_index('registros_importados', 'ix_registros_importados_importacao_id'):
        op.create_index('ix_registros_importados_importacao_id', 'registros_importados', ['importacao_id'], unique=False)

    # registros_importados: composite index status_validacao + criado_em
    if not has_index('registros_importados', 'ix_registros_importados_status_criado_em'):
        op.create_index(
            'ix_registros_importados_status_criado_em',
            'registros_importados',
            ['status_validacao', 'criado_em'],
            unique=False
        )

    # SAAS: re-add unique indexes if missing to align with models
    if not has_index('saas_registros_financeiros', 'ix_saas_financeiros_id_transacao'):
        op.create_index('ix_saas_financeiros_id_transacao', 'saas_registros_financeiros', ['id_transacao'], unique=True)
    if not has_index('saas_registros_operacionais', 'ix_saas_operacionais_id_evento'):
        op.create_index('ix_saas_operacionais_id_evento', 'saas_registros_operacionais', ['id_evento'], unique=True)
    # SAAS: restore non-unique indexes for produtos if missing
    if not has_index('saas_registros_produtos', 'ix_saas_produtos_id_venda'):
        op.create_index('ix_saas_produtos_id_venda', 'saas_registros_produtos', ['id_venda'], unique=False)
    if not has_index('saas_registros_produtos', 'ix_saas_produtos_sku_produto'):
        op.create_index('ix_saas_produtos_sku_produto', 'saas_registros_produtos', ['sku_produto'], unique=False)


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    def has_index(table_name: str, index_name: str) -> bool:
        try:
            idxs = insp.get_indexes(table_name)
            return any(i.get('name') == index_name for i in idxs)
        except Exception:
            return False

    # Drop indexes if exist
    if has_index('usuarios', 'ix_usuarios_email'):
        op.drop_index('ix_usuarios_email', table_name='usuarios')
    if has_index('usuarios', 'ix_usuarios_departamento_id'):
        op.drop_index('ix_usuarios_departamento_id', table_name='usuarios')

    if has_index('atividades_usuarios', 'ix_atividades_usuarios_usuario_id'):
        op.drop_index('ix_atividades_usuarios_usuario_id', table_name='atividades_usuarios')

    if has_index('logs_importacoes', 'ix_logs_importacoes_importacao_id'):
        op.drop_index('ix_logs_importacoes_importacao_id', table_name='logs_importacoes')

    if has_index('registros_importados', 'ix_registros_importados_importacao_id'):
        op.drop_index('ix_registros_importados_importacao_id', table_name='registros_importados')
    if has_index('registros_importados', 'ix_registros_importados_status_criado_em'):
        op.drop_index('ix_registros_importados_status_criado_em', table_name='registros_importados')

    # SAAS: drop unique indexes if exist
    if has_index('saas_registros_financeiros', 'ix_saas_financeiros_id_transacao'):
        op.drop_index('ix_saas_financeiros_id_transacao', table_name='saas_registros_financeiros')
    if has_index('saas_registros_operacionais', 'ix_saas_operacionais_id_evento'):
        op.drop_index('ix_saas_operacionais_id_evento', table_name='saas_registros_operacionais')
    # SAAS: drop non-unique indexes for produtos
    if has_index('saas_registros_produtos', 'ix_saas_produtos_id_venda'):
        op.drop_index('ix_saas_produtos_id_venda', table_name='saas_registros_produtos')
    if has_index('saas_registros_produtos', 'ix_saas_produtos_sku_produto'):
        op.drop_index('ix_saas_produtos_sku_produto', table_name='saas_registros_produtos')

    # Optionally re-create TesteValor to revert
    if not insp.has_table('TesteValor'):
        op.create_table(
            'TesteValor',
            sa.Column('id', sa.Integer, primary_key=True),
            sa.Column('data_extracao', sa.Date, nullable=False),
            sa.Column('receita_total', sa.Numeric),
            sa.Column('receita_media_por_pedido', sa.Numeric),
            sa.Column('total_pedidos', sa.Integer),
            sa.Column('novos_clientes', sa.Integer),
            sa.Column('taxa_conversao_percent', sa.Numeric),
        )
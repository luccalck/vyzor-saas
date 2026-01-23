"""
Add SAAS tables: saas_registros_financeiros, saas_registros_produtos, saas_registros_operacionais

Revision ID: e1a2b3c4d5e6
Revises: 9a79991e19cd
Create Date: 2025-10-19 00:00:00
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e1a2b3c4d5e6'
down_revision = '9a79991e19cd'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # SAAS - Registros Financeiros
    if not insp.has_table('saas_registros_financeiros'):
        op.create_table(
            'saas_registros_financeiros',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('importacao_id', sa.Integer(), sa.ForeignKey('importacoes.id', ondelete='CASCADE'), nullable=False),
            sa.Column('id_transacao', sa.String(length=255), nullable=False, unique=True),
            sa.Column('data_transacao', sa.Date(), nullable=True),
            sa.Column('receita', sa.Numeric(12, 2), nullable=True),
            sa.Column('custo', sa.Numeric(12, 2), nullable=True),
            sa.Column('lucro', sa.Numeric(12, 2), nullable=True),
            sa.Column('centro_custo', sa.String(length=255), nullable=True),
            sa.Column('categoria_financeira', sa.String(length=255), nullable=True),
            sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    existing_indexes_fin = [ix['name'] for ix in (insp.get_indexes('saas_registros_financeiros') if insp.has_table('saas_registros_financeiros') else [])]
    if 'ix_saas_financeiros_id_transacao' not in existing_indexes_fin:
        op.create_index('ix_saas_financeiros_id_transacao', 'saas_registros_financeiros', ['id_transacao'], unique=True)

    # SAAS - Registros de Produtos
    if not insp.has_table('saas_registros_produtos'):
        op.create_table(
            'saas_registros_produtos',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('importacao_id', sa.Integer(), sa.ForeignKey('importacoes.id', ondelete='CASCADE'), nullable=False),
            sa.Column('id_venda', sa.String(length=255), nullable=True),
            sa.Column('sku_produto', sa.String(length=255), nullable=True),
            sa.Column('nome_produto', sa.String(length=255), nullable=True),
            sa.Column('categoria_produto', sa.String(length=255), nullable=True),
            sa.Column('quantidade_vendida', sa.Integer(), nullable=True),
            sa.Column('preco_unitario', sa.Numeric(10, 2), nullable=True),
            sa.Column('id_loja', sa.String(length=255), nullable=True),
            sa.Column('data_venda', sa.Date(), nullable=True),
            sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    existing_indexes_prod = [ix['name'] for ix in (insp.get_indexes('saas_registros_produtos') if insp.has_table('saas_registros_produtos') else [])]
    if 'ix_saas_produtos_id_venda' not in existing_indexes_prod:
        op.create_index('ix_saas_produtos_id_venda', 'saas_registros_produtos', ['id_venda'], unique=False)
    if 'ix_saas_produtos_sku_produto' not in existing_indexes_prod:
        op.create_index('ix_saas_produtos_sku_produto', 'saas_registros_produtos', ['sku_produto'], unique=False)

    # SAAS - Registros Operacionais
    if not insp.has_table('saas_registros_operacionais'):
        op.create_table(
            'saas_registros_operacionais',
            sa.Column('id', sa.Integer(), primary_key=True),
            sa.Column('importacao_id', sa.Integer(), sa.ForeignKey('importacoes.id', ondelete='CASCADE'), nullable=False),
            sa.Column('id_evento', sa.String(length=255), nullable=False, unique=True),
            sa.Column('id_colaborador', sa.String(length=255), nullable=True),
            sa.Column('nome_colaborador', sa.String(length=255), nullable=True),
            sa.Column('departamento', sa.String(length=255), nullable=True),
            sa.Column('data_evento', sa.Date(), nullable=True),
            sa.Column('tipo_evento', sa.String(length=255), nullable=True),
            sa.Column('duracao_minutos', sa.Integer(), nullable=True),
            sa.Column('avaliacao_nps', sa.Integer(), nullable=True),
            sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
    existing_indexes_op = [ix['name'] for ix in (insp.get_indexes('saas_registros_operacionais') if insp.has_table('saas_registros_operacionais') else [])]
    if 'ix_saas_operacionais_id_evento' not in existing_indexes_op:
        op.create_index('ix_saas_operacionais_id_evento', 'saas_registros_operacionais', ['id_evento'], unique=True)


def downgrade():
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # SAAS - Registros Operacionais
    if insp.has_table('saas_registros_operacionais'):
        existing_indexes_op = [ix['name'] for ix in insp.get_indexes('saas_registros_operacionais')]
        if 'ix_saas_operacionais_id_evento' in existing_indexes_op:
            op.drop_index('ix_saas_operacionais_id_evento', table_name='saas_registros_operacionais')
        op.drop_table('saas_registros_operacionais')

    # SAAS - Registros de Produtos
    if insp.has_table('saas_registros_produtos'):
        existing_indexes_prod = [ix['name'] for ix in insp.get_indexes('saas_registros_produtos')]
        if 'ix_saas_produtos_sku_produto' in existing_indexes_prod:
            op.drop_index('ix_saas_produtos_sku_produto', table_name='saas_registros_produtos')
        if 'ix_saas_produtos_id_venda' in existing_indexes_prod:
            op.drop_index('ix_saas_produtos_id_venda', table_name='saas_registros_produtos')
        op.drop_table('saas_registros_produtos')

    # SAAS - Registros Financeiros
    if insp.has_table('saas_registros_financeiros'):
        existing_indexes_fin = [ix['name'] for ix in insp.get_indexes('saas_registros_financeiros')]
        if 'ix_saas_financeiros_id_transacao' in existing_indexes_fin:
            op.drop_index('ix_saas_financeiros_id_transacao', table_name='saas_registros_financeiros')
        op.drop_table('saas_registros_financeiros')
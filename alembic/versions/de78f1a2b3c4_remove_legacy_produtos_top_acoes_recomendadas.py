"""Remove tabelas legadas 'produtos_top' e 'acoes_recomendadas'"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'de78f1a2b3c4'
down_revision = 'cd34ef56ab78'
branch_labels = None
depends_on = None


def upgrade():
    # Drop tables if they exist (safe operation)
    op.execute("DROP TABLE IF EXISTS public.produtos_top CASCADE")
    op.execute("DROP TABLE IF EXISTS public.acoes_recomendadas CASCADE")


def downgrade():
    # Recria as tabelas com o esquema anterior
    op.create_table(
        'produtos_top',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('nome', sa.String, nullable=False),
        sa.Column('vendas', sa.Integer),
        sa.Column('receita', sa.Numeric),
        sa.Column('crescimento', sa.Numeric),
        sa.Column('criado_em', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        'acoes_recomendadas',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('titulo', sa.String, nullable=False),
        sa.Column('descricao', sa.TEXT),
        sa.Column('prioridade', sa.String),
        sa.Column('criado_em', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('atualizado_em', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
    )
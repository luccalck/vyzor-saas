"""remove legacy tables (indicadores, insights, registros_importados, modelos_mapeamento)

Revision ID: df23eed3963f
Revises: de78f1a2b3c4
Create Date: 2025-10-19 20:05:46.695240

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df23eed3963f'
down_revision: Union[str, Sequence[str], None] = 'de78f1a2b3c4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: drop legacy tables safely if they exist."""
    # Use CASCADE to remove dependent constraints
    op.execute("DROP TABLE IF EXISTS public.modelos_mapeamento CASCADE")
    op.execute("DROP TABLE IF EXISTS public.registros_importados CASCADE")
    op.execute("DROP TABLE IF EXISTS public.regras_validacao CASCADE")
    op.execute("DROP TABLE IF EXISTS public.logs_importacoes CASCADE")
    op.execute("DROP TABLE IF EXISTS public.indicadores CASCADE")
    op.execute("DROP TABLE IF EXISTS public.metas_receita CASCADE")
    op.execute("DROP TABLE IF EXISTS public.categorias_produtos CASCADE")
    op.execute("DROP TABLE IF EXISTS public.insights CASCADE")


def downgrade() -> None:
    """Downgrade schema: no-op (tables were legacy; restoring is not supported)."""
    pass

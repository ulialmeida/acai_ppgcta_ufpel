"""Adiciona fragmento e informações de método em CompoundAnalytics

Revision ID: b66cb562d919
Revises: aff338fc8075
Create Date: 2025-04-14 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b66cb562d919'
down_revision = 'aff338fc8075'
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona as novas colunas diretamente na tabela existente
    op.add_column('tbl_compound_analytics', sa.Column('fragment', sa.Float(), nullable=True))
    op.add_column('tbl_compound_analytics', sa.Column('method_description', sa.String(length=255), nullable=True))
    op.add_column('tbl_compound_analytics', sa.Column('chromatographic_condition', sa.String(length=255), nullable=True))
    op.add_column('tbl_compound_analytics', sa.Column('notes', sa.Text(), nullable=True))


def downgrade():
    # Remove as colunas adicionadas
    op.drop_column('tbl_compound_analytics', 'fragment')
    op.drop_column('tbl_compound_analytics', 'method_description')
    op.drop_column('tbl_compound_analytics', 'chromatographic_condition')
    op.drop_column('tbl_compound_analytics', 'notes')
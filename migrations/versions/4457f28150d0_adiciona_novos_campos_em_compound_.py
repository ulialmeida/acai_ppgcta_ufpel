"""adiciona novos campos em compound analytics

Revision ID: 4457f28150d0
Revises: 815eacd1bd8b
Create Date: 2025-04-13 19:28:45.973433

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4457f28150d0'
down_revision = '815eacd1bd8b'
branch_labels = None
depends_on = None


def upgrade():
    # Criar nova tabela com as alterações desejadas
    op.create_table(
        'new_tbl_compound_analytics',
        sa.Column('analytics_id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('compound_id', sa.Integer(), nullable=False),
        sa.Column('matrix_id', sa.Integer(), nullable=False),
        sa.Column('instrument_method', sa.String(), nullable=False),
        # ... inclua os outros campos aqui
    )

    # Copiar os dados da tabela antiga
    op.execute("""
        INSERT INTO new_tbl_compound_analytics (analytics_id, compound_id, matrix_id, instrument_method)
        SELECT analytics_id, compound_id, matrix_id, instrument_method FROM tbl_compound_analytics
    """)

    # Excluir a tabela antiga
    op.drop_table('tbl_compound_analytics')

    # Renomear a nova
    op.rename_table('new_tbl_compound_analytics', 'tbl_compound_analytics')

    # Adicionar a constraint única
    op.create_unique_constraint('uq_compound_matrix_method', 'tbl_compound_analytics',
                                ['compound_id', 'matrix_id', 'instrument_method'])

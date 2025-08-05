"""add_matrix_id_and_unique_constraint_to_analytics

Revision ID: 73b2154c72d8
Revises: 1da3a53984b6
Create Date: 2025-04-11 16:14:46.296150

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '73b2154c72d8'
down_revision = '1da3a53984b6'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('tbl_compound_analytics') as batch_op:
        batch_op.add_column(sa.Column('matrix_id', sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            'fk_compound_analytics_matrix',
            'tbl_matrixes',
            ['matrix_id'],
            ['matrixes_id']
        )
        batch_op.create_unique_constraint(
            'uq_compound_matrix_method',
            ['compound_id', 'matrix_id', 'instrument_method']
        )

def downgrade():
    with op.batch_alter_table('tbl_compound_analytics') as batch_op:
        batch_op.drop_constraint('uq_compound_matrix_method')
        batch_op.drop_constraint('fk_compound_analytics_matrix')
        batch_op.drop_column('matrix_id')
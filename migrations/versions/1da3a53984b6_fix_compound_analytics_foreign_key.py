"""fix compound analytics foreign key

Revision ID: 1da3a53984b6
Revises: 815eacd1bd8b  # HASH DA MIGRAÇÃO ANTERIOR CONFIRMADO
Create Date: 2025-04-11 14:38:20.394154

"""
from alembic import op
import sqlalchemy as sa


# VERIFIQUE ESTAS 4 LINHAS CRITICAMENTE!
revision = '1da3a53984b6'      # DEVE bater com Revision ID
down_revision = '815eacd1bd8b'  # HASH da migração anterior
branch_labels = None
depends_on = None

def upgrade():
    # SQLite não fornece nome para constraints não nomeadas,
    # então precisamos usar uma abordagem diferente
    with op.batch_alter_table('tbl_compound_analytics') as batch_op:
        # Cria a nova FK correta (SQLite vai automaticamente remover a antiga)
        batch_op.create_foreign_key(
            'fk_tbl_compound_analytics_compound_id_correct',  # Nomeamos a nova
            'tbl_compound',
            ['compound_id'],
            ['compound_id']  # Referencia a coluna correta
        )

def downgrade():
    with op.batch_alter_table('tbl_compound_analytics') as batch_op:
        batch_op.drop_constraint('fk_tbl_compound_analytics_compound_id_correct',
                              type_='foreignkey')
        # Recria a FK original (sem nome)
        batch_op.create_foreign_key(
            None,  # SQLite vai nomear automaticamente
            'tbl_compound',
            ['compound_id'],
            ['id']
        )
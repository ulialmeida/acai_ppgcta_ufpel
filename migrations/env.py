import logging
from logging.config import fileConfig
from flask import current_app
from alembic import context
import os
import sys

# Adicione esta parte para importar seus modelos
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app import db  # ou from seu_modulo_principal import db

# Configuração padrão do logging
config = context.config
config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'alembic.ini')
fileConfig(config_path)
logger = logging.getLogger('alembic.env')

# Configuração simplificada do engine
def get_engine():
    return db.engine

def get_engine_url():
    return str(get_engine().url).replace('%', '%%')

config.set_main_option('sqlalchemy.url', get_engine_url())

# Use os metadados diretamente do SQLAlchemy
target_metadata = db.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, 'autogenerate', False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info('No changes in schema detected.')

    connectable = get_engine()

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            compare_type=True,
            compare_server_default=True
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
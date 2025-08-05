from flask_script import Manager
from flask_migrate import Migrate, MigrateCommand
from app import app, db  # Certifique-se que `app` e `db` estão definidos no app.py

migrate = Migrate(app, db)
manager = Manager(app)

manager.add_command('db', MigrateCommand)

if __name__ == '__main__':
    manager.run()

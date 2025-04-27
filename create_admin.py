from werkzeug.security import generate_password_hash
from app import create_app, db
from app.models import User
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_admin():
    app = create_app()
    with app.app_context():
        logger.info("Database URI: %s", app.config['SQLALCHEMY_DATABASE_URI'])
        logger.info("Current directory: %s", os.getcwd())
        logger.info("Instance directory: %s", os.path.join(os.getcwd(), 'instance'))
        
        # Verificar se o banco de dados existe
        db_path = os.path.join(os.getcwd(), 'instance', 'questoespmp.db')
        logger.info("Database path: %s", db_path)
        logger.info("Database exists: %s", os.path.exists(db_path))
        
        # Verificar permissões do banco de dados
        if os.path.exists(db_path):
            logger.info("Database permissions: %s", oct(os.stat(db_path).st_mode)[-3:])
            logger.info("Database owner: %s", os.stat(db_path).st_uid)
            logger.info("Database group: %s", os.stat(db_path).st_gid)
        
        # Verificar se o usuário já existe
        user = User.query.filter_by(username='admin').first()
        logger.info("User found: %s", bool(user))
        
        if not user:
            # Criar novo usuário admin
            admin = User(
                username='admin',
                email='admin@questoespmp.com',
                password_hash=generate_password_hash('admin123')
            )
            db.session.add(admin)
            try:
                db.session.commit()
                logger.info("Usuário admin criado com sucesso!")
            except Exception as e:
                logger.error("Erro ao criar usuário: %s", str(e))
                db.session.rollback()
        else:
            logger.info("Usuário admin já existe!")

if __name__ == '__main__':
    create_admin()

import os
print("Diretório de trabalho atual:", os.getcwd())
print("Caminho absoluto do banco:", os.path.abspath('instance/questoespmp.db'))
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from .config import Config
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv(verbose=True)

# Configurar logging
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Verificar se a chave da API está presente
api_key = os.getenv('OPENAI_API_KEY')
if api_key:
    logger.info("OpenAI API Key encontrada")
else:
    logger.warning("OpenAI API Key não encontrada no arquivo .env")

# Inicialização das extensões
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

# Configuração do Flask-Login
login_manager.login_view = 'main.login'
login_manager.login_message = 'Por favor, faça login para acessar esta página.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from app.models import User
    logger.info(f"Carregando usuário com ID: {user_id}")
    try:
        user = User.query.get(int(user_id))
        if user:
            logger.info(f"Usuário encontrado: {user.username}")
        else:
            logger.warning(f"Usuário não encontrado para ID: {user_id}")
        return user
    except Exception as e:
        logger.error(f"Erro ao carregar usuário: {str(e)}")
        return None

def create_app(config_class=Config):
    """Cria e configura a aplicação Flask"""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Configurar pasta de upload
    app.config['UPLOAD_FOLDER'] = os.path.join(app.instance_path, 'uploads')
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Configuração do logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Criando a aplicação...")
    
    # Inicialização das extensões
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    
    # Registro dos blueprints
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # Inicializar o banco de dados
    with app.app_context():
        from app.database import init_db
        init_db()
    
    return app

import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
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

def create_app():
    """Cria e configura a aplicação Flask"""
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Configuração do logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info("Criando a aplicação...")
    
    # Inicialização das extensões
    db.init_app(app)
    login_manager.init_app(app)
    
    # Registro dos blueprints
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # Criação das tabelas do banco de dados
    with app.app_context():
        try:
            # Verifica se as tabelas já existem
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if not existing_tables:
                logger.info("Criando tabelas do banco de dados...")
                db.create_all()
            else:
                logger.info("Tabelas já existem no banco de dados")
        except Exception as e:
            logger.error(f"Erro ao criar tabelas: {str(e)}")
            raise
    
    return app 
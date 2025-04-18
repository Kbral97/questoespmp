from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicialização das extensões
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

def create_app(config=None):
    # Criar e configurar a aplicação
    app = Flask(__name__)
    
    # Configurações padrão
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev')
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///questoespmp.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Carregar configurações adicionais se fornecidas
    if config:
        app.config.update(config)
    
    # Inicializar extensões
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configurar user_loader
    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Registrar blueprints
    from app.routes import main as main_blueprint
    app.register_blueprint(main_blueprint)
    
    # Criar tabelas do banco de dados
    with app.app_context():
        db.create_all()
    
    return app 
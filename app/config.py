import os
from pathlib import Path
from dotenv import load_dotenv
import secrets
import platform

# Carregar variáveis de ambiente do arquivo .env
env_path = Path('.') / '.env'
load_dotenv(env_path)

# Obter o diretório atual
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

class Config:
    """Configurações da aplicação."""
    
    # Configurações básicas
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'
    
    # Configurações do banco de dados
    DB_PATH = os.path.join(BASE_DIR, 'instance', 'questoespmp.db')
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DB_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações da API OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Configurações de segurança
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora
    
    # Configurações de CSRF
    WTF_CSRF_ENABLED = True
    WTF_CSRF_SECRET_KEY = SECRET_KEY
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hora
    
    @classmethod
    def validate_config(cls):
        """Valida as configurações necessárias."""
        missing = []
        
        if not cls.SECRET_KEY:
            missing.append('SECRET_KEY')
            
        if not cls.OPENAI_API_KEY:
            missing.append('OPENAI_API_KEY')
            
        if not cls.SQLALCHEMY_DATABASE_URI:
            missing.append('SQLALCHEMY_DATABASE_URI')
            
        if missing:
            raise ValueError(
                f"Configurações obrigatórias ausentes: {', '.join(missing)}. "
                "Verifique o arquivo .env e certifique-se de que todas as variáveis necessárias estão definidas."
            ) 
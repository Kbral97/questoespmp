import os
from pathlib import Path
from dotenv import load_dotenv
import secrets

# Carregar variáveis de ambiente do arquivo .env
env_path = Path('.') / '.env'
load_dotenv(env_path)

class Config:
    """Configurações da aplicação."""
    
    # Configurações básicas
    SECRET_KEY = os.getenv('SECRET_KEY') or secrets.token_hex(32)
    FLASK_ENV = os.getenv('FLASK_ENV', 'production')
    DEBUG = os.getenv('FLASK_DEBUG', '0') == '1'
    
    # Configurações do banco de dados
    SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', 'sqlite:///instance/questoespmp.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações da API OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    # Configurações de segurança
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hora
    
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
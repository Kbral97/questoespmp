import os
from pathlib import Path
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
env_path = Path('.') / '.env'
load_dotenv(env_path)

class Config:
    """Configurações da aplicação."""
    
    # Configurações básicas
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', '1')
    
    # Configurações do banco de dados
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Configurações da API OpenAI
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
    
    @classmethod
    def validate_config(cls):
        """Valida as configurações necessárias."""
        missing = []
        
        if not cls.OPENAI_API_KEY:
            missing.append('OPENAI_API_KEY')
            
        if missing:
            raise ValueError(
                f"Configurações obrigatórias ausentes: {', '.join(missing)}. "
                "Verifique o arquivo .env e certifique-se de que todas as variáveis necessárias estão definidas."
            ) 
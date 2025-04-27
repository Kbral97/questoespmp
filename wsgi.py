import os
import logging
import sys

# Adicionar o diretório src ao PYTHONPATH
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.append(src_path)

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log environment variables
logger.info("Environment variables:")
logger.info(f"FLASK_ENV: {os.getenv('FLASK_ENV', 'Not set')}")
logger.info(f"FLASK_DEBUG: {os.getenv('FLASK_DEBUG', 'Not set')}")
logger.info(f"PYTHONPATH: {sys.path}")

# Desabilita completamente o parser de argumentos do Kivy
os.environ['KIVY_NO_ARGS'] = '1'
# Desabilita a interface gráfica do Kivy
os.environ['KIVY_NO_CONSOLELOG'] = '1'
os.environ['KIVY_NO_FILELOG'] = '1'
os.environ['KIVY_NO_ARGS'] = '1'
os.environ['KIVY_NO_CONFIG'] = '1'
os.environ['KIVY_NO_ENV_CONFIG'] = '1'

logger.info("Importando a aplicação Flask...")
# Importa a aplicação Flask
from app import create_app

logger.info("Criando a aplicação...")
app = create_app()

if __name__ == "__main__":
    logger.info("Iniciando o servidor Flask...")
    logger.info(f"Database path: {os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'questoespmp.db')}")
    logger.info(f"Servidor rodando em: http://0.0.0.0:5000")
    app.run(debug=True, host='0.0.0.0', port=5000) 
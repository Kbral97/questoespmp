import logging
import sys
from wsgi import app

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    try:
        logger.info("Iniciando a aplicação...")
        app.run(debug=True)
    except Exception as e:
        logger.error(f"Erro ao iniciar a aplicação: {str(e)}", exc_info=True) 
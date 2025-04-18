import os
import logging

# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
    app.run(debug=True, host='0.0.0.0', port=5000) 
import os
import sys
import logging

def setup_logging():
    """Configura o logging da aplicação de forma centralizada."""
    # Criar diretório de logs se não existir
    log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    
    # Configurar logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(os.path.join(log_dir, 'app.log'))
        ]
    )
    
    # Configurar logger específico para a aplicação
    logger = logging.getLogger('questoespmp')
    logger.setLevel(logging.DEBUG)
    
    return logger 
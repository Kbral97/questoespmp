#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Ponto de entrada principal da aplicação.
"""

import os
import logging
from app import create_app

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main entry point."""
    try:
        # Criar diretório de logs se não existir
        os.makedirs('logs', exist_ok=True)
        
        # Criar a aplicação
        app = create_app()
        
        # Configurar host e porta
        host = os.getenv('FLASK_HOST', '127.0.0.1')
        port = int(os.getenv('FLASK_PORT', 5000))
        
        # Log das configurações
        logger.info(f"Database path: {app.config['SQLALCHEMY_DATABASE_URI']}")
        logger.info(f"Upload folder: {app.config['UPLOAD_FOLDER']}")
        logger.info(f"Server address: http://{host}:{port}")
        
        # Iniciar o servidor
        app.run(host=host, port=port, debug=True)
        
    except Exception as e:
        logger.error(f"Error starting application: {str(e)}")
        logger.error("Stack trace:", exc_info=True)
        raise

if __name__ == '__main__':
    main() 
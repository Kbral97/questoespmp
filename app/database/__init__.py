"""
Database package for PMP Questions Generator.
"""

import os
import sys
import logging

logger = logging.getLogger(__name__)

# Adicionar logs de debug
logger.info("Iniciando importação do módulo database")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Python path: {sys.path}")
logger.info(f"Database directory contents: {os.listdir(os.path.dirname(__file__))}")

try:
    from app.database.db_manager import DatabaseManager
    logger.info("Importação do DatabaseManager bem-sucedida")
except ImportError as e:
    logger.error(f"Erro ao importar DatabaseManager: {e}")
    raise

__all__ = ['DatabaseManager'] 
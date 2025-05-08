#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para executar a migração de dados
"""

import os
import sys
import logging
from migrate_data import DataMigrator

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('migration.log')
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Função principal para executar a migração."""
    try:
        logger.info("Iniciando processo de migração")
        
        # Criar instância do migrador
        migrator = DataMigrator()
        
        # Executar migração
        migrator.run_migration()
        
        logger.info("Migração concluída com sucesso")
        
    except Exception as e:
        logger.error(f"Erro durante a migração: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
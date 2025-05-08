#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para verificar a estrutura das tabelas nos bancos de dados
"""

import os
import sqlite3
import logging
from typing import Dict, List

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_table_structure(conn: sqlite3.Connection, table_name: str) -> List[Dict]:
    """Retorna a estrutura de uma tabela."""
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    return [
        {
            'cid': col[0],
            'name': col[1],
            'type': col[2],
            'notnull': col[3],
            'dflt_value': col[4],
            'pk': col[5]
        }
        for col in columns
    ]

def print_table_structure(table_name: str, structure: List[Dict]):
    """Imprime a estrutura de uma tabela de forma organizada."""
    logger.info(f"\nEstrutura da tabela {table_name}:")
    logger.info("-" * 80)
    logger.info(f"{'Nome':<20} {'Tipo':<15} {'NotNull':<8} {'PK':<5} {'Default':<20}")
    logger.info("-" * 80)
    for col in structure:
        logger.info(
            f"{col['name']:<20} {col['type']:<15} {col['notnull']:<8} "
            f"{col['pk']:<5} {str(col['dflt_value']):<20}"
        )
    logger.info("-" * 80)

def main():
    """Função principal."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    instance_dir = os.path.join(base_dir, 'instance')
    
    # Caminhos dos bancos
    main_db = os.path.join(instance_dir, 'questoespmp.db')
    old_db = os.path.join(instance_dir, 'questions.db')
    
    # Conectar aos bancos
    main_conn = sqlite3.connect(main_db)
    old_conn = sqlite3.connect(old_db)
    
    try:
        # Verificar tabela questions
        logger.info("\n=== Estrutura da tabela questions ===")
        
        # Banco principal
        logger.info("\nBanco principal (questoespmp.db):")
        main_structure = get_table_structure(main_conn, 'questions')
        print_table_structure('questions', main_structure)
        
        # Banco antigo
        logger.info("\nBanco antigo (questions.db):")
        old_structure = get_table_structure(old_conn, 'questions')
        print_table_structure('questions', old_structure)
        
        # Verificar dados de exemplo
        logger.info("\n=== Dados de exemplo ===")
        
        # Banco principal
        logger.info("\nBanco principal (questoespmp.db):")
        main_cursor = main_conn.cursor()
        main_cursor.execute("SELECT * FROM questions LIMIT 1")
        main_row = main_cursor.fetchone()
        if main_row:
            logger.info(f"Colunas: {[desc[0] for desc in main_cursor.description]}")
            logger.info(f"Valores: {main_row}")
        
        # Banco antigo
        logger.info("\nBanco antigo (questions.db):")
        old_cursor = old_conn.cursor()
        old_cursor.execute("SELECT * FROM questions LIMIT 1")
        old_row = old_cursor.fetchone()
        if old_row:
            logger.info(f"Colunas: {[desc[0] for desc in old_cursor.description]}")
            logger.info(f"Valores: {old_row}")
        
    finally:
        main_conn.close()
        old_conn.close()

if __name__ == "__main__":
    main() 
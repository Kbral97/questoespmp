import sqlite3
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_domains():
    """Lista todos os domínios da tabela domains"""
    try:
        conn = sqlite3.connect('instance/questoespmp.db')
        cursor = conn.cursor()
        
        # Listar todos os domínios
        cursor.execute("SELECT id, name, description FROM domains ORDER BY id")
        domains = cursor.fetchall()
        
        logger.info("\nLista completa de domínios:")
        logger.info("-" * 50)
        for domain in domains:
            logger.info(f"ID: {domain[0]}")
            logger.info(f"Nome: {domain[1]}")
            logger.info(f"Descrição: {domain[2]}")
            logger.info("-" * 50)
            
    except Exception as e:
        logger.error(f"Erro ao listar domínios: {str(e)}")
        raise e
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    list_domains() 
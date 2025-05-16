import sqlite3
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_all_domains():
    """Verifica todos os registros e seus domínios"""
    try:
        conn = sqlite3.connect('instance/questoespmp.db')
        cursor = conn.cursor()
        
        # Contar total de registros
        cursor.execute("SELECT COUNT(*) FROM topic_summaries")
        total = cursor.fetchone()[0]
        logger.info(f"\nTotal de registros na tabela: {total}")
        
        # Buscar todos os registros
        cursor.execute("""
            SELECT id, document_title, domains
            FROM topic_summaries 
            ORDER BY id
        """)
        
        rows = cursor.fetchall()
        
        for row in rows:
            id = row[0]
            doc = row[1]
            domains_json = row[2]
            
            logger.info(f"\nRegistro ID {id} (Documento: {doc}):")
            logger.info(f"Domains (raw): {domains_json}")
            
            try:
                domains = json.loads(domains_json)
                logger.info(f"Domains (parsed): {domains}")
                logger.info(f"Type: {type(domains)}")
                
                if isinstance(domains, list):
                    if domains and isinstance(domains[0], dict):
                        logger.info("Formato: Lista de objetos")
                        for domain in domains:
                            logger.info(f"  - {domain}")
                    else:
                        logger.info("Formato: Lista de strings")
                        for domain in domains:
                            logger.info(f"  - {domain}")
                else:
                    logger.info(f"Formato: {type(domains)}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Erro ao verificar domínios: {str(e)}")
        raise e
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    check_all_domains() 
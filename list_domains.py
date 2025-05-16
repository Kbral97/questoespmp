import sqlite3
import json
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def list_domain_names():
    """Lista todos os valores do campo name dentro do campo domains da tabela topic_summaries"""
    try:
        conn = sqlite3.connect('instance/questoespmp.db')
        cursor = conn.cursor()
        
        # Buscar todos os registros da tabela topic_summaries
        cursor.execute("SELECT id, domains FROM topic_summaries")
        rows = cursor.fetchall()
        
        # Conjunto para armazenar nomes únicos
        unique_domains = set()
        
        # Processar cada registro
        for row in rows:
            id = row[0]
            domains_json = row[1]
            
            try:
                domains = json.loads(domains_json)
                logger.info(f"\nRegistro ID {id}:")
                
                # Se domains é uma lista de objetos
                if isinstance(domains, list) and domains and isinstance(domains[0], dict):
                    for domain in domains:
                        if 'name' in domain:
                            unique_domains.add(domain['name'])
                            logger.info(f"  - {domain['name']}")
                # Se domains é uma lista de strings
                elif isinstance(domains, list):
                    for domain in domains:
                        unique_domains.add(domain)
                        logger.info(f"  - {domain}")
                        
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON para ID {id}: {e}")
                continue
        
        # Mostrar lista final de domínios únicos
        logger.info("\nLista final de domínios únicos encontrados:")
        for domain in sorted(unique_domains):
            logger.info(f"  - {domain}")
            
    except Exception as e:
        logger.error(f"Erro ao listar domínios: {str(e)}")
        raise e
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    list_domain_names() 
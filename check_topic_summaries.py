import sqlite3
import logging
import json

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_topic_summaries():
    """Verifica o conteúdo da tabela topic_summaries"""
    try:
        conn = sqlite3.connect('instance/questoespmp.db')
        cursor = conn.cursor()
        
        # Verificar estrutura da tabela
        cursor.execute("PRAGMA table_info(topic_summaries)")
        columns = cursor.fetchall()
        logger.info("\nEstrutura da tabela topic_summaries:")
        logger.info("-" * 50)
        for column in columns:
            logger.info(f"Coluna: {column[1]}, Tipo: {column[2]}")
        logger.info("-" * 50)
        
        # Contar total de registros
        cursor.execute("SELECT COUNT(*) FROM topic_summaries")
        total = cursor.fetchone()[0]
        logger.info(f"\nTotal de registros na tabela: {total}")
        
        # Listar todos os registros
        cursor.execute("""
            SELECT ts.id, ts.document_title, ts.topic, ts.summary, ts.domains, ts.created_at, ts.updated_at
            FROM topic_summaries ts
            ORDER BY ts.id
        """)
        summaries = cursor.fetchall()
        
        logger.info("\nRegistros na tabela topic_summaries:")
        logger.info("-" * 50)
        for summary in summaries:
            logger.info(f"ID: {summary[0]}")
            logger.info(f"Documento: {summary[1]}")
            logger.info(f"Tópico: {summary[2]}")
            try:
                domains = json.loads(summary[4])
                if isinstance(domains, list) and domains and isinstance(domains[0], dict):
                    domain_names = [d['name'] for d in domains if 'name' in d]
                else:
                    domain_names = domains
                logger.info(f"Domínios: {', '.join(domain_names)}")
            except json.JSONDecodeError:
                logger.info(f"Domínios: {summary[4]}")
            logger.info(f"Resumo: {summary[3][:100]}...")  # Primeiros 100 caracteres
            logger.info(f"Criado em: {summary[5]}")
            logger.info(f"Atualizado em: {summary[6]}")
            logger.info("-" * 50)
            
    except Exception as e:
        logger.error(f"Erro ao verificar topic_summaries: {str(e)}")
        raise e
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    check_topic_summaries() 
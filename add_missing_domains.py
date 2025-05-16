import sqlite3
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_missing_domains():
    """Adiciona os domínios que estão faltando na tabela domains"""
    try:
        conn = sqlite3.connect('instance/questoespmp.db')
        cursor = conn.cursor()
        
        # Lista de domínios que precisam ser adicionados
        missing_domains = [
            ('Gestão das Aquisições', 'Processos necessários para comprar ou adquirir produtos, serviços ou resultados necessários de fora da equipe do projeto.'),
            ('Gestão de Stakeholders', 'Processos necessários para identificar as pessoas, grupos ou organizações que podem impactar ou ser impactados pelo projeto.')
        ]
        
        # Adicionar cada domínio que está faltando
        for name, description in missing_domains:
            cursor.execute("""
                INSERT OR IGNORE INTO domains (name, description)
                VALUES (?, ?)
            """, (name, description))
            
        conn.commit()
        logger.info("Domínios adicionados com sucesso")
        
        # Listar todos os domínios após a adição
        cursor.execute("SELECT id, name, description FROM domains ORDER BY id")
        domains = cursor.fetchall()
        
        logger.info("\nLista atualizada de domínios:")
        logger.info("-" * 50)
        for domain in domains:
            logger.info(f"ID: {domain[0]}")
            logger.info(f"Nome: {domain[1]}")
            logger.info(f"Descrição: {domain[2]}")
            logger.info("-" * 50)
            
    except Exception as e:
        logger.error(f"Erro ao adicionar domínios: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise e
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    add_missing_domains() 
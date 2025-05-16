import sqlite3
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_domains_table():
    """Atualiza a estrutura da tabela domains adicionando as colunas de auditoria"""
    try:
        conn = sqlite3.connect('instance/questoespmp.db')
        cursor = conn.cursor()
        
        # Desativar chaves estrangeiras temporariamente
        cursor.execute("PRAGMA foreign_keys=OFF;")
        cursor.execute("BEGIN TRANSACTION;")
        
        # Criar uma tabela temporária com a estrutura correta
        cursor.execute("""
            CREATE TABLE domains_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Copiar os dados existentes para a nova tabela
        cursor.execute("""
            INSERT INTO domains_temp (id, name, description)
            SELECT id, name, description FROM domains
        """)
        
        # Atualizar as colunas de auditoria com a data atual
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE domains_temp
            SET created_at = ?,
                updated_at = ?
            WHERE created_at IS NULL
        """, (current_time, current_time))
        
        # Remover a tabela original e renomear a temporária
        cursor.execute("DROP TABLE domains;")
        cursor.execute("ALTER TABLE domains_temp RENAME TO domains;")
        
        # Recriar o índice único
        cursor.execute("CREATE UNIQUE INDEX idx_domains_name ON domains(name);")
        
        # Commit das alterações
        cursor.execute("COMMIT;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        
        conn.commit()
        logger.info("Tabela domains atualizada com sucesso")
        
        # Listar todos os domínios
        cursor.execute("SELECT id, name, description, created_at, updated_at FROM domains ORDER BY id")
        domains = cursor.fetchall()
        
        logger.info("\nLista final de domínios:")
        logger.info("-" * 50)
        for domain in domains:
            logger.info(f"ID: {domain[0]}")
            logger.info(f"Nome: {domain[1]}")
            logger.info(f"Descrição: {domain[2]}")
            logger.info(f"Criado em: {domain[3]}")
            logger.info(f"Atualizado em: {domain[4]}")
            logger.info("-" * 50)
            
    except Exception as e:
        logger.error(f"Erro ao atualizar tabela domains: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise e
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    update_domains_table() 
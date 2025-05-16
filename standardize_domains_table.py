import sqlite3
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def standardize_domains_table():
    """Padroniza os nomes dos domínios na tabela domains"""
    try:
        conn = sqlite3.connect('instance/questoespmp.db')
        cursor = conn.cursor()
        
        # Mapeamento de nomes antigos para novos
        domain_mapping = {
            'Gerenciamento da Integração': 'Gestão da Integração',
            'Gerenciamento do Escopo': 'Gestão do Escopo',
            'Gerenciamento do Cronograma': 'Gestão do Tempo',
            'Gerenciamento dos Custos': 'Gestão do Custo',
            'Gerenciamento da Qualidade': 'Gestão da Qualidade',
            'Gerenciamento dos Recursos': 'Gestão de Recursos',
            'Gerenciamento das Comunicações': 'Gestão das Comunicações',
            'Gerenciamento dos Riscos': 'Gestão dos Riscos',
            'Gerenciamento das Aquisições': 'Gestão das Aquisições',
            'Gerenciamento das Partes Interessadas': 'Gestão de Stakeholders'
        }
        
        # Primeiro, remover a restrição de unicidade temporariamente
        cursor.execute("PRAGMA foreign_keys=OFF;")
        cursor.execute("BEGIN TRANSACTION;")
        
        # Criar uma tabela temporária com a estrutura correta
        cursor.execute("""
            CREATE TABLE domains_temp (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT
            )
        """)
        
        # Inserir os domínios padronizados na tabela temporária
        for old_name, new_name in domain_mapping.items():
            cursor.execute("""
                INSERT INTO domains_temp (name)
                SELECT DISTINCT ?
                FROM domains
                WHERE name = ?
            """, (new_name, old_name))
            
        # Garantir que todos os domínios padrão estejam presentes
        default_domains = [
            'Gestão da Integração',
            'Gestão do Escopo',
            'Gestão do Tempo',
            'Gestão do Custo',
            'Gestão da Qualidade',
            'Gestão de Recursos',
            'Gestão das Comunicações',
            'Gestão dos Riscos',
            'Gestão das Aquisições',
            'Gestão de Stakeholders'
        ]
        
        # Primeiro, inserir todos os domínios padrão
        for domain in default_domains:
            cursor.execute("""
                INSERT OR IGNORE INTO domains_temp (name)
                VALUES (?)
            """, (domain,))
            
        # Verificar se Gestão das Aquisições está presente
        cursor.execute("SELECT COUNT(*) FROM domains_temp WHERE name = ?", ('Gestão das Aquisições',))
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("Adicionando 'Gestão das Aquisições' que estava faltando")
            cursor.execute("""
                INSERT INTO domains_temp (name)
                VALUES (?)
            """, ('Gestão das Aquisições',))
        
        # Remover a tabela original e renomear a temporária
        cursor.execute("DROP TABLE domains;")
        cursor.execute("ALTER TABLE domains_temp RENAME TO domains;")
        
        # Recriar a restrição de unicidade
        cursor.execute("CREATE UNIQUE INDEX idx_domains_name ON domains(name);")
        
        # Commit das alterações
        cursor.execute("COMMIT;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        
        conn.commit()
        logger.info("Domínios padronizados com sucesso")
        
        # Listar os domínios após a padronização
        cursor.execute("SELECT id, name FROM domains ORDER BY id")
        domains = cursor.fetchall()
        logger.info("Lista final de domínios:")
        for domain in domains:
            logger.info(f"ID: {domain[0]}, Nome: {domain[1]}")
            
    except Exception as e:
        logger.error(f"Erro ao padronizar domínios: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise e
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    standardize_domains_table() 
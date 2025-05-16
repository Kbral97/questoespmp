import sqlite3
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def recreate_domains_table():
    """Recria a tabela domains do zero com todos os domínios necessários"""
    try:
        conn = sqlite3.connect('instance/questoespmp.db')
        cursor = conn.cursor()
        
        # Lista de todos os domínios necessários
        domains = [
            ('Gestão da Integração', 'Processos e atividades necessários para identificar, definir, combinar, unificar e coordenar os vários processos e atividades do gerenciamento de projetos.'),
            ('Gestão do Escopo', 'Processos necessários para garantir que o projeto inclua todo o trabalho necessário, e apenas o trabalho necessário, para completar o projeto com sucesso.'),
            ('Gestão do Tempo', 'Processos necessários para gerenciar o término pontual do projeto.'),
            ('Gestão do Custo', 'Processos envolvidos em planejamento, estimativa, orçamentação, financiamento, gerenciamento e controle de custos.'),
            ('Gestão da Qualidade', 'Processos e atividades da organização executora que determinam as políticas de qualidade, os objetivos e as responsabilidades.'),
            ('Gestão de Recursos', 'Processos que organizam, gerenciam e lideram a equipe do projeto.'),
            ('Gestão das Comunicações', 'Processos necessários para garantir que as informações do projeto sejam geradas, coletadas, distribuídas, armazenadas, recuperadas e organizadas de maneira oportuna e apropriada.'),
            ('Gestão dos Riscos', 'Processos de condução do planejamento do gerenciamento de riscos, identificação, análise, planejamento de respostas e monitoramento e controle de riscos em um projeto.'),
            ('Gestão das Aquisições', 'Processos necessários para comprar ou adquirir produtos, serviços ou resultados necessários de fora da equipe do projeto.'),
            ('Gestão de Stakeholders', 'Processos necessários para identificar as pessoas, grupos ou organizações que podem impactar ou ser impactados pelo projeto.')
        ]
        
        # Desativar chaves estrangeiras temporariamente
        cursor.execute("PRAGMA foreign_keys=OFF;")
        cursor.execute("BEGIN TRANSACTION;")
        
        # Remover a tabela existente
        cursor.execute("DROP TABLE IF EXISTS domains;")
        
        # Criar a nova tabela com as colunas de auditoria
        cursor.execute("""
            CREATE TABLE domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Inserir todos os domínios
        current_time = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        for name, description in domains:
            cursor.execute("""
                INSERT INTO domains (name, description, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (name, description, current_time, current_time))
        
        # Recriar o índice único
        cursor.execute("CREATE UNIQUE INDEX idx_domains_name ON domains(name);")
        
        # Commit das alterações
        cursor.execute("COMMIT;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        
        conn.commit()
        logger.info("Tabela domains recriada com sucesso")
        
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
        logger.error(f"Erro ao recriar tabela domains: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
        raise e
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    recreate_domains_table() 
"""
Database package for PMP Questions Generator.
"""

import os
import sys
import logging
from app import db

logger = logging.getLogger(__name__)

# Adicionar logs de debug
logger.info("Iniciando importação do módulo database")
logger.info(f"Current directory: {os.getcwd()}")
logger.info(f"Python path: {sys.path}")
logger.info(f"Database directory contents: {os.listdir(os.path.dirname(__file__))}")

print("Caminho absoluto do banco:", os.path.abspath("instance/questoespmp.db"))

try:
    from app.database.db_manager import DatabaseManager
    logger.info("Importação do DatabaseManager bem-sucedida")
except ImportError as e:
    logger.error(f"Erro ao importar DatabaseManager: {e}")
    raise

__all__ = ['DatabaseManager']

def init_default_domains():
    """Inicializa os domínios padrão do PMBOK se não existirem"""
    from app.models import Domain
    
    logger.info("Iniciando criação dos domínios padrão...")
    
    default_domains = [
        {
            'name': 'Gerenciamento da Integração',
            'description': 'Processos e atividades necessários para identificar, definir, combinar, unificar e coordenar os vários processos e atividades do gerenciamento de projetos.'
        },
        {
            'name': 'Gerenciamento do Escopo',
            'description': 'Processos necessários para garantir que o projeto inclua todo o trabalho necessário, e apenas ele, para completar o projeto com sucesso.'
        },
        {
            'name': 'Gerenciamento do Cronograma',
            'description': 'Processos necessários para gerenciar o término do projeto no prazo.'
        },
        {
            'name': 'Gerenciamento dos Custos',
            'description': 'Processos envolvidos em planejamento, estimativa, orçamentação, financiamento, gerenciamento e controle dos custos.'
        },
        {
            'name': 'Gerenciamento da Qualidade',
            'description': 'Processos e atividades da organização executora que determinam as políticas de qualidade, os objetivos e as responsabilidades.'
        },
        {
            'name': 'Gerenciamento dos Recursos',
            'description': 'Processos que organizam, gerenciam e lideram a equipe do projeto.'
        },
        {
            'name': 'Gerenciamento das Comunicações',
            'description': 'Processos necessários para garantir que as informações do projeto sejam geradas, coletadas, distribuídas, armazenadas, recuperadas e organizadas.'
        },
        {
            'name': 'Gerenciamento dos Riscos',
            'description': 'Processos de condução do planejamento do gerenciamento de riscos, identificação, análise, planejamento de respostas e monitoramento e controle dos riscos.'
        },
        {
            'name': 'Gerenciamento das Aquisições',
            'description': 'Processos necessários para comprar ou adquirir produtos, serviços ou resultados necessários de fora da equipe do projeto.'
        },
        {
            'name': 'Gerenciamento das Partes Interessadas',
            'description': 'Processos necessários para identificar as pessoas, grupos ou organizações que podem impactar ou ser impactados pelo projeto.'
        }
    ]
    
    try:
        # Verificar se a tabela domains existe
        inspector = db.inspect(db.engine)
        if 'domains' not in inspector.get_table_names():
            logger.info("Tabela 'domains' não encontrada. Criando tabela...")
            Domain.__table__.create(db.engine)
            logger.info("Tabela 'domains' criada com sucesso.")
        
        # Inserir domínios padrão
        for domain_data in default_domains:
            domain = Domain.query.filter_by(name=domain_data['name']).first()
            if not domain:
                logger.info(f"Criando domínio: {domain_data['name']}")
                domain = Domain(**domain_data)
                db.session.add(domain)
        
        db.session.commit()
        logger.info("Domínios padrão inicializados com sucesso.")
        
    except Exception as e:
        logger.error(f"Erro ao inicializar domínios: {str(e)}")
        db.session.rollback()
        raise e

def init_db():
    """Inicializa o banco de dados"""
    logger.info("Iniciando inicialização do banco de dados...")
    try:
        db.create_all()
        logger.info("Tabelas do banco de dados criadas com sucesso.")
        init_default_domains()
    except Exception as e:
        logger.error(f"Erro ao inicializar banco de dados: {str(e)}")
        raise e 
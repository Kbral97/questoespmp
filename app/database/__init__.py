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
    try:
        from app.models import Domain
        from app import db
    
        # Lista de domínios padrão do PMBOK (exatamente como usados na tabela topic_summaries)
        default_domains = [
            {
                'name': 'Gestão da Integração',
                'description': 'Processos e atividades necessários para identificar, definir, combinar, unificar e coordenar os vários processos e atividades do gerenciamento de projetos.'
            },
            {
                'name': 'Gestão do Escopo',
                'description': 'Processos necessários para garantir que o projeto inclua todo o trabalho necessário, e apenas ele, para completar o projeto com sucesso.'
            },
            {
                'name': 'Gestão do Tempo',
                'description': 'Processos necessários para gerenciar o término do projeto no prazo.'
            },
            {
                'name': 'Gestão do Custo',
                'description': 'Processos envolvidos em planejamento, estimativa, orçamentação, financiamento, gerenciamento e controle dos custos.'
            },
            {
                'name': 'Gestão da Qualidade',
                'description': 'Processos e atividades da organização executora que determinam as políticas de qualidade, os objetivos e as responsabilidades.'
            },
            {
                'name': 'Gestão de Recursos',
                'description': 'Processos que organizam, gerenciam e lideram a equipe do projeto.'
            },
            {
                'name': 'Gestão das Comunicações',
                'description': 'Processos necessários para garantir que as informações do projeto sejam geradas, coletadas, distribuídas, armazenadas, recuperadas e organizadas de maneira oportuna e apropriada.'
            },
            {
                'name': 'Gestão dos Riscos',
                'description': 'Processos de condução do planejamento do gerenciamento de riscos, identificação, análise, planejamento de respostas e monitoramento e controle dos riscos do projeto.'
            },
            {
                'name': 'Gestão das Aquisições',
                'description': 'Processos necessários para comprar ou adquirir produtos, serviços ou resultados necessários de fora da equipe do projeto.'
            },
            {
                'name': 'Gestão de Stakeholders',
                'description': 'Processos necessários para identificar as pessoas, grupos ou organizações que podem impactar ou ser impactados pelo projeto.'
            }
        ]
    
        # Verificar e adicionar domínios que não existem
        for domain_data in default_domains:
            domain = Domain.query.filter_by(name=domain_data['name']).first()
            if not domain:
                domain = Domain(
                    name=domain_data['name'],
                    description=domain_data['description']
                )
                db.session.add(domain)
                logger.info(f"Domínio adicionado: {domain_data['name']}")
            else:
                # Atualizar descrição se o domínio já existir
                domain.description = domain_data['description']
                logger.info(f"Domínio atualizado: {domain_data['name']}")
        
        db.session.commit()
        logger.info("Domínios padrão inicializados com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao inicializar domínios padrão: {str(e)}")
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
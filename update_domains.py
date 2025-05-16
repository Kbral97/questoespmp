from app import db
from app.models import Domain
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_domains():
    """Atualiza os nomes dos domínios para corresponder aos nomes usados na tabela topic_summaries"""
    try:
        # Mapeamento de nomes antigos para novos
        domain_mapping = {
            'Gerenciamento da Integração': 'Gestão da Integração',
            'Gerenciamento do Escopo': 'Gestão do Escopo',
            'Gerenciamento do Cronograma': 'Gestão do Tempo',
            'Gerenciamento dos Custos': 'Gestão do Custo',
            'Gerenciamento da Qualidade': 'Gestão da Qualidade',
            'Gerenciamento dos Recursos': 'Gestão de Recursos Humanos',
            'Gerenciamento das Comunicações': 'Gestão das Comunicações',
            'Gerenciamento dos Riscos': 'Gestão dos Riscos',
            'Gerenciamento das Aquisições': 'Gestão das Aquisições',
            'Gerenciamento das Partes Interessadas': 'Gestão de Stakeholders'
        }
        
        # Atualizar cada domínio
        for old_name, new_name in domain_mapping.items():
            domain = Domain.query.filter_by(name=old_name).first()
            if domain:
                logger.info(f"Atualizando domínio de '{old_name}' para '{new_name}'")
                domain.name = new_name
            else:
                logger.info(f"Domínio '{old_name}' não encontrado")
        
        # Commit das alterações
        db.session.commit()
        logger.info("Domínios atualizados com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao atualizar domínios: {str(e)}")
        db.session.rollback()
        raise e

if __name__ == '__main__':
    update_domains() 
import sqlite3
import json
import logging
import difflib

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_official_domains():
    """Busca os nomes oficiais dos domínios na tabela domains"""
    conn = sqlite3.connect('instance/questoespmp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM domains")
    domains = [row[0] for row in cursor.fetchall()]
    conn.close()
    return domains

def add_domain_if_not_exists(domain_name, description):
    """Adiciona um domínio na tabela domains se ele não existir"""
    conn = sqlite3.connect('instance/questoespmp.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM domains WHERE name = ?", (domain_name,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO domains (name, description) VALUES (?, ?)", (domain_name, description))
        conn.commit()
        logger.info(f"Domínio '{domain_name}' adicionado à tabela domains.")
    conn.close()

def find_best_match(name, official_domains):
    """Encontra o nome oficial mais próximo usando similaridade"""
    match = difflib.get_close_matches(name, official_domains, n=1, cutoff=0.7)
    return match[0] if match else name

def standardize_domains():
    """Padroniza os nomes dos domínios na tabela topic_summaries para os nomes oficiais da tabela domains"""
    try:
        conn = sqlite3.connect('instance/questoespmp.db')
        cursor = conn.cursor()
        
        # Adicionar 'Gestão da Qualidade' se não existir
        add_domain_if_not_exists('Gestão da Qualidade', 'Processos e atividades da organização executora que determinam as políticas de qualidade, os objetivos e as responsabilidades.')
        
        official_domains = get_official_domains()
        logger.info(f"Domínios oficiais: {official_domains}")
        
        # Buscar todos os registros
        cursor.execute("SELECT id, domains FROM topic_summaries")
        rows = cursor.fetchall()
        
        # Atualizar cada registro
        for row in rows:
            id = row[0]
            domains_json = row[1]
            try:
                domains = json.loads(domains_json)
                updated_domains = []
                # Se domains é uma lista de objetos
                if isinstance(domains, list) and domains and isinstance(domains[0], dict):
                    for domain in domains:
                        if 'name' in domain:
                            old_name = domain['name']
                            if old_name in ['Gestão de Recursos Humanos', 'Gerenciamento dos Recursos']:
                                new_name = 'Gestão de Recursos'
                            else:
                                new_name = find_best_match(old_name, official_domains)
                            domain['name'] = new_name
                            updated_domains.append(domain)
                # Se domains é uma lista de strings
                elif isinstance(domains, list):
                    for domain in domains:
                        if domain in ['Gestão de Recursos Humanos', 'Gerenciamento dos Recursos']:
                            new_name = 'Gestão de Recursos'
                        else:
                            new_name = find_best_match(domain, official_domains)
                        updated_domains.append(new_name)
                # Atualizar o registro
                cursor.execute(
                    "UPDATE topic_summaries SET domains = ? WHERE id = ?",
                    (json.dumps(updated_domains), id)
                )
                logger.info(f"Registro ID {id} atualizado")
            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON para ID {id}: {e}")
                continue
        # Commit das alterações
        conn.commit()
        logger.info("Domínios padronizados com sucesso")
    except Exception as e:
        logger.error(f"Erro ao padronizar domínios: {str(e)}")
        raise e
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == '__main__':
    standardize_domains() 
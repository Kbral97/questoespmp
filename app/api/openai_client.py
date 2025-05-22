#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OpenAI Client para geração de questões PMP - Versão Web
"""

import os
import json
import logging
import time
from pathlib import Path
from openai import OpenAI
import openai
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any, Tuple, Union
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import csv
from ..database.db_manager import DatabaseManager
import random
from app.models import Domain, AIModel
from app import db
import traceback
import httpx

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log da versão da biblioteca OpenAI
logger.info(f"[OPENAI] Versão da biblioteca OpenAI: {openai.__version__}")

# Criar uma única instância do DatabaseManager
db_manager = DatabaseManager()

def get_training_file_path(filename):
    """Retorna o caminho do arquivo de treinamento"""
    return os.path.join('training_data', filename)

def get_model_file_path(model_id):
    """Retorna o caminho do arquivo do modelo"""
    return os.path.join('models', f'{model_id}.json')

def save_training_data(data, filename):
    """Salva os dados de treinamento em um arquivo"""
    os.makedirs('training_data', exist_ok=True)
    with open(get_training_file_path(filename), 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def save_model_info(model_id, model_info):
    """Salva as informações do modelo em um arquivo"""
    os.makedirs('models', exist_ok=True)
    with open(get_model_file_path(model_id), 'w', encoding='utf-8') as f:
        json.dump(model_info, f, ensure_ascii=False, indent=2)

def load_model_info(model_id):
    """Carrega as informações do modelo de um arquivo"""
    try:
        with open(get_model_file_path(model_id), 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def list_available_models():
    """Lista os modelos disponíveis"""
    models = []
    if os.path.exists('models'):
        for file in os.listdir('models'):
            if file.endswith('.json'):
                model_id = file[:-5]  # Remove .json
                model_info = load_model_info(model_id)
                if model_info:
                    models.append({
                        'id': model_id,
                        'name': model_info.get('name', model_id),
                        'description': model_info.get('description', ''),
                        'created_at': model_info.get('created_at', '')
                    })
    return models

def get_openai_client():
    """
    Cria e retorna uma instância do cliente OpenAI.
    """
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("API key não encontrada nas variáveis de ambiente")
        
        # Inicializar cliente com a sintaxe correta para a versão mais recente
        client = OpenAI(
            api_key=api_key,
            base_url=os.getenv('OPENAI_API_BASE', 'https://api.openai.com/v1'),
            http_client=httpx.Client(
                timeout=httpx.Timeout(30.0, read=30.0, write=30.0, connect=30.0)
            )
        )
        logger.info("[OPENAI] Cliente inicializado com sucesso")
        return client
        
    except Exception as e:
        logger.error(f"[OPENAI] Erro ao criar cliente OpenAI: {str(e)}")
        logger.error(f"[OPENAI] Stack trace: {traceback.format_exc()}")
        raise

def find_relevant_training_data(query: str, top_k: int = 3) -> List[Dict]:
    """Encontra os dados de treinamento mais relevantes para uma consulta"""
    training_data = db_manager.get_all_training_data()
    
    if not training_data:
        return []
    
    # Extrair textos para comparação
    texts = [item['content'] for item in training_data]
    texts.append(query)
    
    # Criar vetorizador TF-IDF
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(texts)
    
    # Calcular similaridade
    query_vector = tfidf_matrix[-1]
    similarities = cosine_similarity(query_vector, tfidf_matrix[:-1])[0]
    
    # Ordenar por similaridade
    indices = np.argsort(similarities)[::-1][:top_k]
    
    return [training_data[i] for i in indices]

def get_enhanced_prompt(base_prompt: str, relevant_files: List[Dict]) -> str:
    """Melhora o prompt com base nos arquivos relevantes"""
    if not relevant_files:
        return base_prompt
    
    enhanced_prompt = f"{base_prompt}\n\nContexto relevante:\n"
    for file in relevant_files:
        enhanced_prompt += f"\n{file['content']}\n"
    
    return enhanced_prompt

def generate_topic_summary(topic_text, client, api_key=None):
    """
    Gera um resumo do tópico usando a API do OpenAI.
    """
    try:
        logger.info("[SUMMARY] Iniciando geração de resumo")
        logger.info(f"[SUMMARY] Tamanho do texto recebido: {len(topic_text)} caracteres")
        
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("API key não encontrada")
        
        # Inicializar cliente se não fornecido
        if not client:
            client = OpenAI(api_key=api_key)
        
        # Limpar e preparar o texto
        cleaned_text = ' '.join(topic_text.split())  # Remove espaços extras
        logger.info(f"[SUMMARY] Texto limpo: {cleaned_text[:200]}...")
        
        # Prompt para gerar o resumo
        prompt = f"""
        Analise o seguinte texto sobre um tópico do PMBOK e gere um resumo detalhado incluindo:

        1. Resumo Conciso:
           - Um resumo claro e objetivo do tópico
           - Principais conceitos e definições
           - Contexto dentro do PMBOK

        2. Pontos-Chave:
           - Cada ponto deve ser específico e detalhado
           - Incluir explicações e justificativas
           - Relacionar com outros conceitos do PMBOK quando relevante
           - Destacar aspectos práticos e teóricos

        3. Exemplos Práticos:
           - Exemplos reais de aplicação
           - Casos de uso comuns
           - Situações do dia a dia do gerenciamento de projetos

        4. Referências ao PMBOK:
           - Seções específicas do PMBOK
           - Relações com outros processos
           - Áreas de conhecimento relacionadas

        5. Domínios do PMP:
           - Lista de domínios do PMP relacionados
           - Explicação da relação com cada domínio
           - Impacto nos processos de cada domínio

        TEXTO:
        {cleaned_text}
        
        Retorne no seguinte formato JSON:
        {{
            "summary": "resumo conciso e detalhado",
            "key_points": [
                {{
                    "point": "ponto principal",
                    "explanation": "explicação detalhada",
                    "pmbok_relation": "relação com PMBOK"
                }}
            ],
            "practical_examples": [
                {{
                    "example": "exemplo prático",
                    "context": "contexto de aplicação",
                    "lessons": "lições aprendidas"
                }}
            ],
            "pmbok_references": [
                {{
                    "section": "seção do PMBOK",
                    "description": "descrição da referência",
                    "relevance": "relevância para o tópico"
                }}
            ],
            "domains": [
                {{
                    "name": "nome do domínio",
                    "relation": "relação com o tópico",
                    "impact": "impacto nos processos"
                }}
            ]
        }}
        """
        
        logger.info("[SUMMARY] Enviando requisição para OpenAI")
        # Fazer a chamada à API
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um especialista em PMP e está analisando tópicos do PMBOK. Seu objetivo é fornecer análises detalhadas e práticas que ajudem na compreensão e aplicação dos conceitos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000  # Aumentando o limite de tokens
        )
        
        logger.info("[SUMMARY] Resposta recebida da OpenAI")
        
        # Extrair e validar a resposta
        try:
            content = response.choices[0].message.content
            logger.info(f"[SUMMARY] Conteúdo da resposta: {content[:200]}...")
            
            result = json.loads(content)
            logger.info("[SUMMARY] JSON decodificado com sucesso")
            
            # Validar campos obrigatórios
            required_fields = ['summary', 'key_points', 'practical_examples', 'pmbok_references', 'domains']
            for field in required_fields:
                if field not in result:
                    logger.error(f"[SUMMARY] Campo obrigatório ausente: {field}")
                    return None
                if not result[field]:
                    logger.error(f"[SUMMARY] Campo {field} está vazio")
                    return None
            
            # Validar estrutura dos pontos-chave
            if not isinstance(result['key_points'], list):
                logger.error("[SUMMARY] Formato inválido para pontos-chave")
                return None
            
            logger.info("[SUMMARY] Resumo gerado com sucesso")
            logger.info(f"[SUMMARY] Número de pontos-chave: {len(result['key_points'])}")
            logger.info(f"[SUMMARY] Número de exemplos práticos: {len(result['practical_examples'])}")
            logger.info(f"[SUMMARY] Número de referências PMBOK: {len(result['pmbok_references'])}")
            logger.info(f"[SUMMARY] Número de domínios: {len(result['domains'])}")
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"[SUMMARY] Erro ao decodificar JSON da resposta: {str(e)}")
            logger.error(f"[SUMMARY] Conteúdo da resposta: {content}")
            return None
            
        except Exception as e:
            logger.error(f"[SUMMARY] Erro ao processar resposta da API: {str(e)}")
            logger.error("[SUMMARY] Stack trace:", exc_info=True)
            return None
        
    except Exception as e:
        logger.error(f"[SUMMARY] Erro ao gerar resumo: {str(e)}")
        logger.error("[SUMMARY] Stack trace:", exc_info=True)
        return None

def get_least_used_summaries(topic: str, num_summaries: int = 2) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Seleciona os dois resumos menos representados nas questões existentes do tópico.
    
    Args:
        topic: Tópico para buscar questões
        num_summaries: Número de resumos a serem retornados (padrão: 2)
        
    Returns:
        Tuple contendo o resumo principal e o resumo relacionado
    """
    logger.info(f"[SUMMARIES] Buscando resumos menos usados para tópico {topic}")
    
    try:
        # Buscar todas as questões do tópico
        questions = db_manager.get_questions_by_topic(topic)
        
        # Contar uso de cada resumo
        summary_usage = {}
        for question in questions:
            metadata = question.get('metadata', {})
            used_summaries = metadata.get('used_summaries', [])
            for summary_id in used_summaries:
                summary_usage[summary_id] = summary_usage.get(summary_id, 0) + 1
        
        # Buscar todos os resumos disponíveis
        all_summaries = db_manager.get_all_summaries()
        
        # Ordenar resumos por uso (menos usados primeiro)
        sorted_summaries = sorted(
            all_summaries,
            key=lambda x: summary_usage.get(x['id'], 0)
        )
        
        # Selecionar os dois menos usados
        selected_summaries = sorted_summaries[:num_summaries]
        
        if len(selected_summaries) < num_summaries:
            logger.warning(f"[SUMMARIES] Apenas {len(selected_summaries)} resumos disponíveis")
            # Preencher com resumos aleatórios se necessário
            while len(selected_summaries) < num_summaries:
                random_summary = random.choice(all_summaries)
                if random_summary not in selected_summaries:
                    selected_summaries.append(random_summary)
        
        logger.info(f"[SUMMARIES] Resumos selecionados: {[s['id'] for s in selected_summaries]}")
        return selected_summaries[0], selected_summaries[1] if len(selected_summaries) > 1 else None
        
    except Exception as e:
        logger.error(f"[SUMMARIES] Erro ao selecionar resumos: {str(e)}")
        return None, None

def normalize_model_response(question_data):
    """
    Normaliza a resposta do modelo para garantir o formato correto.
    A pergunta já contém o cenário, então retornamos apenas um campo.
    """
    if isinstance(question_data, str):
        question = question_data.strip()
        return {
            'question': question
        }
    elif isinstance(question_data, dict):
        # Se for um dicionário, usa o campo question ou scenario
        if 'question' in question_data:
            return {
                'question': question_data['question']
            }
        elif 'scenario' in question_data:
            return {
                'question': question_data['scenario']
            }
    return None

def generate_questions(topic, num_questions, api_key, summary=None):
    logger.info(f"[GENERATE] Iniciando geração de {num_questions} questões sobre {topic}")
    
    try:
        # Inicializar cliente OpenAI usando a função get_openai_client
        client = get_openai_client()
        logger.info("[GENERATE] Cliente OpenAI inicializado")
        
        # Buscar modelos padrão
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT model_type, model_id 
                FROM ai_models 
                WHERE is_default = 1
            """)
            default_models = {row[0]: row[1] for row in cursor.fetchall()}
            logger.info(f"[GENERATE] Modelos padrão encontrados: {default_models}")
            
            if not default_models:
                raise ValueError("Nenhum modelo padrão configurado")
        
        # Preparar o contexto do resumo e extrair informações para o frontend
        summary_context = ""
        frontend_summary = {
            'summary': '',
            'key_points': []
        }
        
        if summary:
            if isinstance(summary, dict):
                # Contexto para geração
                summary_context = f"""Contexto do tópico principal:
{summary.get('summary', 'Sem resumo disponível')}

Pontos-chave do tópico principal:
{chr(10).join([f"- {point['point']}: {point['explanation']}" for point in summary.get('key_points', [])]) if summary.get('key_points') else 'Sem pontos-chave disponíveis'}

Exemplos práticos:
{chr(10).join([f"- {example['example']}: {example['context']}" for example in summary.get('practical_examples', [])]) if summary.get('practical_examples') else 'Sem exemplos disponíveis'}

Referências PMBOK:
{chr(10).join([f"- {ref['section']}: {ref['description']}" for ref in summary.get('pmbok_references', [])]) if summary.get('pmbok_references') else 'Sem referências disponíveis'}"""
                
                # Dados para o frontend
                frontend_summary = {
                    'summary': summary.get('summary', ''),
                    'key_points': [f"{point['point']}: {point['explanation']}" for point in summary.get('key_points', [])]
                }
            else:
                # Se o resumo for uma string, usa diretamente
                summary_context = f"""Contexto do tópico principal:
{summary}"""
                frontend_summary = {
                    'summary': summary,
                    'key_points': []
                }
        
        questions = []
        for i in range(num_questions):
            logger.info(f"[QUESTION_AI] Iniciando geração de pergunta {i+1} para tópico {topic}")
            
            try:
                # Gerar questão usando o modelo de questões
                question_data = generate_question(
                    topic=topic,
                    summary=summary_context,
                    client=client  # Passando o cliente como parâmetro
                )
                
                if not question_data:
                    logger.error("[QUESTION_AI] Falha ao gerar questão")
                    continue
                
                # Gerar resposta usando o modelo de respostas
                answer_data = generate_answer_with_ai(
                    question_data=question_data,
                    topic=topic,
                    subtopic=None,
                    client=client,
                    api_key=api_key,
                    model=default_models['answer'],
                    topic_summary=summary,
                    related_summary=None
                )
                
                if not answer_data:
                    logger.error("[ANSWER_AI] Falha ao gerar resposta")
                    continue
                
                # Gerar distratores usando o modelo de distratores
                distractors_data, warnings = generate_distractors(
                    question_data=question_data,
                    answer_data=answer_data,
                    topic=topic,
                    subtopic=None,
                    client=client,
                    api_key=api_key,
                    model=default_models['distractor'],
                    topic_summary=summary,
                    related_summary=None
                )
                
                if not distractors_data:
                    logger.error("[DISTRACTORS] Falha ao gerar distratores")
                    continue
                
                # Combinar todos os dados
                question_data = {
                    'question': question_data.get('question', ''),
                    'correct_answer': answer_data.get('correct_answer', ''),
                    'explanation': answer_data.get('justification', ''),
                    'justification': answer_data.get('justification', ''),
                    'distractors': distractors_data.get('distractors', []),
                    'warnings': warnings,
                    'options': distractors_data.get('distractors', []) + [answer_data.get('correct_answer', '')],
                    'topic_summary': frontend_summary['summary'],
                    'topic_key_points': frontend_summary['key_points']
                }
                
                # Garantir que todos os campos sejam strings ou listas vazias
                for key, value in question_data.items():
                    if value is None:
                        question_data[key] = [] if isinstance(question_data.get(key, []), list) else ''
                    elif isinstance(value, list):
                        question_data[key] = [str(item) for item in value]
                    else:
                        question_data[key] = str(value)
                
                questions.append(question_data)
                logger.info(f"[QUESTION_AI] Questão {i+1} gerada com sucesso")
                
            except Exception as e:
                logger.error(f"[QUESTION_AI] Erro ao gerar questão {i+1}: {str(e)}")
                logger.error(f"[QUESTION_AI] Stack trace: {traceback.format_exc()}")
                continue
            
        if not questions:
            logger.error("[GENERATE] Nenhuma questão foi gerada com sucesso")
            return None
            
        # Retornar apenas o array de questões, com o resumo e key points incluídos em cada questão
        return questions
        
    except Exception as e:
        logger.error(f"[GENERATE] Erro ao gerar questões: {str(e)}")
        logger.error(f"[GENERATE] Stack trace: {traceback.format_exc()}")
        return None

def format_training_data(questions):
    """Formata as questões para treinamento"""
    training_data = []
    for question in questions:
        training_data.append({
            'question': question['question'],
            'answer': question['answer'],
            'distractors': question['distractors'],
            'explanation': question.get('explanation', ''),
            'topic': question.get('topic', '')
        })
    return training_data

def tune_model(training_data, api_key=None, model_name="gpt-3.5-turbo"):
    """Ajusta um modelo com os dados de treinamento"""
    client = get_openai_client()
    
    # Formatar dados para treinamento
    formatted_data = format_training_data(training_data)
    
    # Criar arquivo de treinamento
    training_file = f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    save_training_data(formatted_data, training_file)
    
    # Iniciar treinamento
    try:
        response = client.fine_tuning.jobs.create(
            training_file=training_file,
            model=model_name,
            hyperparameters={
                "n_epochs": 3
            }
        )
        return response.id
    except Exception as e:
        logger.error(f"Erro ao ajustar modelo: {str(e)}")
        return None

def get_tuning_status(job_id, api_key=None):
    """Obtém o status do ajuste do modelo"""
    client = get_openai_client()
    try:
        response = client.fine_tuning.jobs.retrieve(job_id)
        return {
            'status': response.status,
            'model_id': response.fine_tuned_model if hasattr(response, 'fine_tuned_model') else None
        }
    except Exception as e:
        logger.error(f"Erro ao obter status do ajuste: {str(e)}")
        return None

def validate_question_quality(question: Dict) -> bool:
    """Valida a qualidade de uma questão"""
    required_fields = ['question', 'options', 'correct_answer', 'explanation', 'topic']
    for field in required_fields:
        if field not in question or not question[field]:
            logger.error(f"[VALIDATION] Campo obrigatório ausente ou vazio: {field}")
            return False
    
    if not isinstance(question['options'], list) or len(question['options']) < 4:
        logger.error("[VALIDATION] Número insuficiente de opções")
        return False
    
    if not isinstance(question['correct_answer'], int) or question['correct_answer'] < 0 or question['correct_answer'] >= len(question['options']):
        logger.error("[VALIDATION] Índice da resposta correta inválido")
        return False
    
    return True

def map_model_id_to_api(model_id: str) -> str:
    """Mapeia um ID de modelo para o nome da API"""
    model_mapping = {
        'gpt-3.5': 'gpt-3.5-turbo',
        'gpt-4': 'gpt-4',
        'default': 'gpt-3.5-turbo'
    }
    return model_mapping.get(model_id, model_mapping['default'])

def process_openai_response(response_text):
    """Processa a resposta da OpenAI"""
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        logger.error("Erro ao decodificar resposta da OpenAI")
        return None

def generate_question(topic, summary, client=None):
    """Gera uma questão sobre um tópico específico usando o contexto fornecido."""
    try:
        logger.info(f"[QUESTION_AI] Iniciando geração de pergunta para tópico {topic}")
        logger.info("[QUESTION_AI] Combinando contexto dos resumos")
        
        # Inicializar cliente se não fornecido
        if client is None:
            logger.info("[QUESTION_AI] Cliente não fornecido, inicializando novo cliente")
            client = get_openai_client()
        
        # Construir o prompt com instruções mais claras sobre o formato JSON
        prompt = f'''Gere um cenário e uma pergunta sobre {topic}.

O cenário deve ser realista e contextualizado com a prática de gerenciamento de projetos.
A pergunta deve ser clara e objetiva, sem incluir as alternativas.

Contexto do tópico principal:
{summary}

IMPORTANTE: Você DEVE retornar APENAS um objeto JSON válido com exatamente este formato:
{{
    "scenario": "Descrição do cenário",
    "question": "Pergunta baseada no cenário"
}}

Exemplo de resposta esperada:
{{
    "scenario": "Você é um gerente de projetos responsável por implementar um novo sistema de gestão em uma empresa. O projeto tem um prazo de 6 meses e um orçamento limitado.",
    "question": "Qual é o primeiro documento que você deve desenvolver para iniciar o projeto?"
}}'''

        logger.info("[QUESTION_AI] Enviando requisição para OpenAI")
        response = client.chat.completions.create(
            model=os.getenv('QUESTION_MODEL_ID', 'gpt-3.5-turbo'),
            messages=[
                {"role": "system", "content": "Você é um especialista em criar cenários e questões de gerenciamento de projetos. Sua resposta DEVE ser um objeto JSON válido."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        content = response.choices[0].message.content.strip()
        logger.info(f"[QUESTION_AI] Resposta recebida: {content[:100]}...")
        
        # Tentar extrair JSON da resposta
        try:
            # Primeiro, tenta decodificar diretamente
            question_data = json.loads(content)
        except json.JSONDecodeError:
            # Se falhar, tenta encontrar um objeto JSON na resposta
            import re
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    question_data = json.loads(json_match.group(0))
                except json.JSONDecodeError as e:
                    logger.error(f"[QUESTION_AI] Erro ao extrair JSON da resposta: {str(e)}")
                    raise
            else:
                logger.error("[QUESTION_AI] Nenhum JSON encontrado na resposta")
                raise ValueError("Resposta não contém JSON válido")
        
        # Validar estrutura do JSON
        if not isinstance(question_data, dict):
            logger.error(f"[QUESTION_AI] Resposta não é um dicionário: {type(question_data)}")
            raise ValueError("Resposta não é um dicionário")
            
        required_fields = ['scenario', 'question']
        missing_fields = [field for field in required_fields if field not in question_data]
        if missing_fields:
            logger.error(f"[QUESTION_AI] Campos obrigatórios ausentes: {missing_fields}")
            raise ValueError(f"Campos obrigatórios ausentes: {missing_fields}")
            
        logger.info("[QUESTION_AI] Questão gerada com sucesso")
        return question_data
        
    except Exception as e:
        logger.error(f"[QUESTION_AI] Erro ao gerar pergunta: {str(e)}")
        raise

def generate_answer_with_ai(
    question_data: Dict[str, str],
    topic: str,
    subtopic: str,
    client: Any,
    api_key: str,
    model: str = None,
    topic_summary: Dict[str, Any] = None,
    related_summary: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Gera a resposta correta com justificativa detalhada.
    Esta é a função atual para geração de respostas.
    """
    logger.info(f"[ANSWER_AI] Iniciando geração de resposta para tópico {topic}")
    
    try:
        # Preparar o contexto do resumo
        summary_context = ""
        if topic_summary:
            if isinstance(topic_summary, dict):
                summary_context = f"""Contexto do tópico principal:
{topic_summary.get('summary', 'Sem resumo disponível')}

Pontos-chave do tópico principal:
{chr(10).join([f"- {point['point']}: {point['explanation']}" for point in topic_summary.get('key_points', [])]) if topic_summary.get('key_points') else 'Sem pontos-chave disponíveis'}

Exemplos práticos:
{chr(10).join([f"- {example['example']}: {example['context']}" for example in topic_summary.get('practical_examples', [])]) if topic_summary.get('practical_examples') else 'Sem exemplos disponíveis'}

Referências PMBOK:
{chr(10).join([f"- {ref['section']}: {ref['description']}" for ref in topic_summary.get('pmbok_references', [])]) if topic_summary.get('pmbok_references') else 'Sem referências disponíveis'}"""
            else:
                # Se o resumo for uma string, usa diretamente
                summary_context = f"""Contexto do tópico principal:
{topic_summary}"""

        if related_summary:
            if isinstance(related_summary, dict):
                summary_context += f"\n\nTópico relacionado: {related_summary.get('topic', 'Sem tópico')}\n"
                summary_context += f"Resumo: {related_summary.get('summary', 'Sem resumo')}\n"
                summary_context += "Pontos-chave:\n"
                summary_context += chr(10).join([f"- {point['point']}: {point['explanation']}" for point in related_summary.get('key_points', [])])
            else:
                summary_context += f"\n\nTópico relacionado:\n{related_summary}"
        
        prompt = f"""Analise o seguinte cenário e pergunta sobre {topic}:

{question_data['question']}

{summary_context}

Gere uma resposta detalhada que inclua:
1. A resposta correta
2. Uma justificativa completa explicando por que esta é a resposta correta
3. Referências específicas ao PMBOK e boas práticas de gerenciamento de projetos
4. Exemplos práticos que ajudem a entender o conceito

IMPORTANTE: Você DEVE retornar APENAS um objeto JSON válido com exatamente este formato:
{{
    "correct_answer": "Texto da resposta correta",
    "justification": "Explicação detalhada de por que esta é a resposta correta",
    "pmbok_references": ["Referência 1", "Referência 2"],
    "practical_examples": ["Exemplo 1", "Exemplo 2"]
}}

NÃO inclua nenhum texto antes ou depois do JSON.
NÃO inclua aspas ou formatação adicional.
O JSON DEVE ser válido e seguir exatamente o formato especificado."""

        logger.info("[ANSWER_AI] Enviando requisição para OpenAI")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos com profundo conhecimento do PMBOK e certificação PMP. Sua resposta DEVE ser APENAS um objeto JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        response_text = response.choices[0].message.content.strip()
        logger.info(f"[ANSWER_AI] Resposta recebida: {response_text[:200]}...")
        
        try:
            # Tentar extrair JSON da resposta
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                answer_data = json.loads(json_str)
            else:
                logger.error(f"[ANSWER_AI] Nenhum JSON encontrado na resposta: {response_text}")
                return None

            logger.info("[ANSWER_AI] JSON decodificado com sucesso")
        except json.JSONDecodeError as e:
            logger.error(f"[ANSWER_AI] Erro ao decodificar JSON: {response_text}")
            logger.error(f"[ANSWER_AI] Erro específico: {str(e)}")
            return None

        if not isinstance(answer_data, dict):
            logger.error(f"[ANSWER_AI] Formato inválido: {answer_data}")
            return None

        required_fields = {
            "correct_answer": str,
            "justification": str,
            "pmbok_references": list,
            "practical_examples": list
        }

        for field, expected_type in required_fields.items():
            if field not in answer_data:
                logger.error(f"[ANSWER_AI] Campo ausente: {field}")
                return None
            if not isinstance(answer_data[field], expected_type):
                logger.error(f"[ANSWER_AI] Tipo inválido para {field}: esperado {expected_type}, recebido {type(answer_data[field])}")
                return None

        for field in ["pmbok_references", "practical_examples"]:
            if not all(isinstance(item, str) for item in answer_data[field]):
                logger.error(f"[ANSWER_AI] Itens inválidos na lista {field}")
                return None

        # Validar usando a função validate_answer
        if not validate_answer(answer_data):
            logger.error("[ANSWER_AI] Falha na validação da resposta")
            return None

        answer_data["prompt"] = prompt
        answer_data["raw_response"] = response_text

        logger.info("[ANSWER_AI] Resposta gerada com sucesso")
        return answer_data

    except Exception as e:
        logger.error(f"[ANSWER_AI] Erro ao gerar resposta: {str(e)}")
        return None

def generate_distractors(
    question_data: Dict[str, str],
    answer_data: Dict[str, Any],
    topic: str,
    subtopic: str,
    client: Any,
    api_key: str,
    model: str = None,
    topic_summary: Union[Dict[str, Any], str] = None,
    related_summary: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Gera distratores baseados na pergunta e resposta correta.
    Esta é a função atual para geração de distratores.
    """
    logger.info(f"[DISTRACTORS] Iniciando geração de distratores para tópico {topic}")
    
    try:
        # Combinar contexto dos resumos
        logger.info("[DISTRACTORS] Combinando contexto dos resumos")
        
        # Tratar o resumo do tópico principal
        if isinstance(topic_summary, dict):
            logger.info("[DISTRACTORS] Processando resumo como dicionário")
            summary_text = topic_summary.get('summary', 'Sem resumo disponível')
            key_points = topic_summary.get('key_points', [])
            key_points_text = chr(10).join([f"- {point['point']}: {point['explanation']}" for point in key_points]) if key_points else 'Sem pontos-chave disponíveis'
        else:
            logger.info("[DISTRACTORS] Processando resumo como string")
            summary_text = topic_summary if topic_summary else 'Sem resumo disponível'
            key_points_text = 'Sem pontos-chave disponíveis'
            
        combined_context = f"""Contexto do tópico principal:
{summary_text}

Pontos-chave do tópico principal:
{key_points_text}"""

        correct_answer_length = len(answer_data['correct_answer'].split())
        allowed_difference = max(3, int(correct_answer_length * 0.3))
        min_length = max(10, correct_answer_length - allowed_difference)
        max_length = correct_answer_length + allowed_difference

        prompt = f"""Analise o seguinte cenário, pergunta e resposta correta sobre {topic}:

Pergunta:
{question_data['question']}

Resposta Correta:
{answer_data['correct_answer']}

Justificativa da Resposta:
{answer_data['justification']}

{combined_context}

CRÍTICO: Você DEVE retornar APENAS um array JSON válido com exatamente 3 strings.
NÃO inclua nenhum texto antes ou depois do JSON.
NÃO inclua aspas ou formatação adicional.
O JSON DEVE ser um array de strings.

Exemplo de resposta esperada:
[
    "Primeira alternativa incorreta",
    "Segunda alternativa incorreta",
    "Terceira alternativa incorreta"
]

As alternativas incorretas devem:
1. Ser plausíveis e relacionadas ao contexto
2. Parecer corretas à primeira vista
3. Ter o mesmo nível de complexidade da resposta correta
4. Ser diferentes entre si
5. Não serem obviamente incorretas
6. Ter entre {min_length} e {max_length} palavras (a resposta correta tem {correct_answer_length} palavras, permitindo uma diferença de {allowed_difference} palavras)"""

        logger.info("[DISTRACTORS] Enviando requisição para OpenAI")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um especialista em criar alternativas plausíveis para questões de gerenciamento de projetos. Sua resposta DEVE ser APENAS um array JSON válido."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        response_text = response.choices[0].message.content.strip()
        logger.info(f"[DISTRACTORS] Resposta recebida: {response_text[:200]}...")
        
        try:
            # Tentar extrair JSON da resposta
            import re
            json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                distractors = json.loads(json_str)
            else:
                logger.error(f"[DISTRACTORS] Nenhum array JSON encontrado na resposta: {response_text}")
                return None, ["Erro ao gerar distratores: formato inválido"]

            logger.info("[DISTRACTORS] JSON decodificado com sucesso")
        except json.JSONDecodeError as e:
            logger.error(f"[DISTRACTORS] Erro ao decodificar JSON: {response_text}")
            logger.error(f"[DISTRACTORS] Erro específico: {str(e)}")
            return None, ["Erro ao gerar distratores: formato inválido"]

        if not isinstance(distractors, list) or len(distractors) != 3:
            logger.error(f"[DISTRACTORS] Formato inválido: {distractors}")
            return None, ["Erro ao gerar distratores: número incorreto de alternativas"]

        if not all(isinstance(d, str) for d in distractors):
            logger.error(f"[DISTRACTORS] Tipos inválidos: {distractors}")
            return None, ["Erro ao gerar distratores: formato inválido"]

        all_options = distractors + [answer_data['correct_answer']]
        if len(set(all_options)) != 4:
            logger.error(f"[DISTRACTORS] Distratores duplicados ou iguais à resposta correta: {distractors}")
            return None, ["Erro ao gerar distratores: alternativas duplicadas"]

        warnings = []
        for i, distractor in enumerate(distractors):
            distractor_length = len(distractor.split())
            if distractor_length < min_length or distractor_length > max_length:
                warnings.append(f"Distrator {i+1} tem {distractor_length} palavras (recomendado: {min_length}-{max_length})")

        logger.info("[DISTRACTORS] Distratores gerados com sucesso")
        return {
            "distractors": distractors,
            "prompt": prompt,
            "raw_response": response_text,
            "warnings": warnings if warnings else []
        }, []

    except Exception as e:
        logger.error(f"[DISTRACTORS] Erro ao gerar distratores: {str(e)}")
        return None, [f"Erro ao gerar distratores: {str(e)}"]

def process_chunks_with_ai(chunks):
    """
    Processa chunks de texto usando a API do OpenAI.
    """
    try:
        logger.info("[PROCESS] Iniciando processamento de chunks")
        
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("API key não encontrada")
        
        # Inicializar cliente
        client = OpenAI(api_key=api_key)
        
        processed_chunks = []
        
        for chunk in chunks:
            try:
                # Prompt para processar o chunk
                prompt = f"""
                Analise o seguinte texto e extraia:
                1. Conceitos principais
                2. Palavras-chave
                3. Relações com outros tópicos do PMBOK
                
                TEXTO:
                {chunk['content']}
                
                Retorne no seguinte formato JSON:
                {{
                    "main_concepts": ["conceito 1", "conceito 2", ...],
                    "keywords": ["palavra 1", "palavra 2", ...],
                    "related_topics": ["tópico 1", "tópico 2", ...]
                }}
                """
                
                # Fazer a chamada à API
                response = client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "Você é um especialista em PMP analisando textos do PMBOK."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                
                # Processar resposta
                content = response.choices[0].message.content
                result = json.loads(content)
                
                # Adicionar resultado processado
                processed_chunk = {
                    'id': chunk['id'],
                    'content': chunk['content'],
                    'processed_data': result
                }
                processed_chunks.append(processed_chunk)
                
                logger.info(f"[PROCESS] Chunk {chunk['id']} processado com sucesso")
                
            except Exception as e:
                logger.error(f"[PROCESS] Erro ao processar chunk {chunk['id']}: {str(e)}")
                continue
        
        logger.info(f"[PROCESS] {len(processed_chunks)} chunks processados com sucesso")
        return processed_chunks
        
    except Exception as e:
        logger.error(f"[PROCESS] Erro ao processar chunks: {str(e)}")
        return None

def validate_answer(answer_data):
    """Valida a resposta da IA"""
    try:
        logger.info("[ANSWER_AI] Iniciando validação da resposta")
        logger.info(f"[ANSWER_AI] Dados recebidos: {answer_data}")
        
        # Verifica se todos os campos obrigatórios estão presentes
        required_fields = ['correct_answer', 'justification', 'pmbok_references', 'practical_examples']
        for field in required_fields:
            if field not in answer_data:
                logger.error(f"[ANSWER_AI] Campo obrigatório ausente: {field}")
                return False
            if not answer_data[field] and not (isinstance(answer_data[field], list)):
                logger.error(f"[ANSWER_AI] Campo vazio não permitido: {field}")
                return False
        
        logger.info("[ANSWER_AI] Resposta validada com sucesso")
        return True
    except Exception as e:
        logger.error(f"[ANSWER_AI] Erro na validação: {str(e)}")
        return False

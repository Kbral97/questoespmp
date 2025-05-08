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
from datetime import datetime
from typing import List, Dict, Optional, Callable, Any, Tuple
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import csv
from app.database.db_manager import DatabaseManager
import random
from app.models import Domain
from app import db

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def get_openai_client(api_key=None):
    """Retorna um cliente OpenAI configurado"""
    if api_key is None:
        api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("API key não encontrada")
    return OpenAI(api_key=api_key)

def find_relevant_training_data(query: str, top_k: int = 3) -> List[Dict]:
    """Encontra os dados de treinamento mais relevantes para uma consulta"""
    db = DatabaseManager()
    training_data = db.get_all_training_data()
    
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

def generate_topic_summary(text: str, client: Any, api_key: str) -> Dict[str, Any]:
    """Gera um resumo estruturado de um tópico usando GPT-4"""
    try:
        logger.info("Iniciando geração de resumo para tópico")
        
        # Buscar domínios do banco de dados
        domains = Domain.query.all()
        domain_names = [domain.name for domain in domains]
        
        prompt = f"""Analise o seguinte texto sobre gerenciamento de projetos e forneça um resumo estruturado:

{text}

Forneça a resposta no seguinte formato JSON:
{{
    "summary": "Um resumo conciso do tópico",
    "key_points": [
        {{
            "concept": "Nome do conceito",
            "definition": "Definição clara e objetiva"
        }}
    ],
    "practical_examples": [
        "Exemplo prático 1",
        "Exemplo prático 2"
    ],
    "pmbok_references": [
        "Referência 1 do PMBOK",
        "Referência 2 do PMBOK"
    ],
    "domains": [
        "Nome do domínio 1",
        "Nome do domínio 2"
    ]
}}

IMPORTANTE:
1. O campo 'domains' deve ser uma lista simples de strings, não uma lista dentro de outra lista
2. Selecione apenas os domínios relevantes da seguinte lista: {domain_names}
3. Mantenha o resumo conciso e focado nos aspectos mais importantes do tópico
4. A resposta DEVE ser um JSON válido, não um texto livre
5. O campo 'domains' é OBRIGATÓRIO e deve conter pelo menos um domínio da lista fornecida"""

        logger.info("Enviando requisição para OpenAI")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos. Sua resposta DEVE ser um JSON válido e DEVE incluir o campo 'domains'."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        logger.info("Resposta recebida da OpenAI")
        content = response.choices[0].message.content.strip()
        
        try:
            result = json.loads(content)
            logger.info("JSON decodificado com sucesso")
            
            # Validar se o campo domains está presente e não vazio
            if 'domains' not in result or not result['domains']:
                logger.error("Campo 'domains' ausente ou vazio na resposta")
                raise Exception("Resposta inválida: campo 'domains' ausente ou vazio")
                
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON: {str(e)}")
            logger.error(f"Conteúdo recebido: {content}")
            raise Exception("Erro ao processar resposta da API")
            
    except Exception as e:
        logger.error(f"Erro ao gerar resumo: {str(e)}")
        raise

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
        db = DatabaseManager()
        questions = db.get_questions_by_topic(topic)
        
        # Contar uso de cada resumo
        summary_usage = {}
        for question in questions:
            metadata = question.get('metadata', {})
            used_summaries = metadata.get('used_summaries', [])
            for summary_id in used_summaries:
                summary_usage[summary_id] = summary_usage.get(summary_id, 0) + 1
        
        # Buscar todos os resumos disponíveis
        all_summaries = db.get_all_summaries()
        
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

def generate_questions(topic: str, num_questions: int, api_key: str) -> List[Dict[str, str]]:
    """
    Gera questões usando a API da OpenAI em 3 etapas:
    1. Geração da pergunta
    2. Geração da resposta e justificativa
    3. Geração dos distratores
    """
    logger.info(f"[GENERATION] Iniciando geração de {num_questions} questões para tópico {topic}")
    questions = []
    retries = 3
    
    try:
        client = OpenAI(api_key=api_key)
        
        for i in range(num_questions):
            logger.info(f"[GENERATION] Gerando questão {i+1}/{num_questions}")
            
            # Selecionar resumos menos usados
            topic_summary, related_summary = get_least_used_summaries(topic)
            if not topic_summary:
                logger.error("[GENERATION] Não foi possível obter resumos")
                continue
                
            logger.info(f"[GENERATION] Usando resumos: {topic_summary['id']} e {related_summary['id'] if related_summary else 'None'}")
            
            # Etapa 1: Gerar pergunta
            question_data = generate_question_with_ai(
                topic=topic,
                subtopic=topic,  # Usando o tópico como subtópico já que não usamos mais subtópicos
                client=client,
                api_key=api_key,
                topic_summary=topic_summary,
                related_summary=related_summary
            )
            
            if not question_data:
                logger.error(f"[GENERATION] Falha ao gerar pergunta para questão {i+1}")
                continue

            # Etapa 2: Gerar resposta e justificativa
            answer_data = generate_answer_with_ai(
                question_data=question_data,
                topic=topic,
                subtopic=topic,
                client=client,
                api_key=api_key,
                topic_summary=topic_summary,
                related_summary=related_summary
            )
            
            if not answer_data:
                logger.error(f"[GENERATION] Falha ao gerar resposta para questão {i+1}")
                continue

            # Etapa 3: Gerar distratores
            distractors_data, warnings = generate_distractors(
                question_data=question_data,
                answer_data=answer_data,
                topic=topic,
                subtopic=topic,
                client=client,
                api_key=api_key,
                topic_summary=topic_summary,
                related_summary=related_summary
            )
            
            if not distractors_data:
                logger.error(f"[GENERATION] Falha ao gerar distratores para questão {i+1}")
                continue

            # Montar questão completa
            question = {
                'question': question_data['full_question'],
                'options': distractors_data['distractors'] + [answer_data['correct_answer']],
                'correct_answer': len(distractors_data['distractors']),  # Índice da resposta correta
                'explanation': answer_data['justification'],
                'topic': topic,
                'created_at': datetime.now().isoformat(),
                'metadata': {
                    'pmbok_references': answer_data['pmbok_references'],
                    'practical_examples': answer_data['practical_examples'],
                    'warnings': warnings + distractors_data['warnings'],
                    'used_summaries': [topic_summary['id']] + ([related_summary['id']] if related_summary else [])
                }
            }
            
            # Validar questão
            if validate_question_quality(question):
                questions.append(question)
                logger.info(f"[GENERATION] Questão {i+1} gerada com sucesso")
            else:
                logger.error(f"[GENERATION] Questão {i+1} falhou na validação")

        logger.info(f"[GENERATION] Geração concluída. Total de questões geradas: {len(questions)}")
        return questions

    except Exception as e:
        logger.error(f"[GENERATION] Erro ao gerar questões: {str(e)}")
        raise

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
    client = get_openai_client(api_key)
    
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
    client = get_openai_client(api_key)
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

def generate_question_with_ai(
    topic: str,
    subtopic: str,
    client: Any,
    api_key: str,
    model: str = None,
    topic_summary: Dict[str, Any] = None,
    related_summary: Dict[str, Any] = None
) -> Dict[str, str]:
    """
    Gera apenas o cenário e a pergunta usando IA.
    Esta é a função atual para geração de perguntas.
    
    Args:
        topic: Tópico principal
        subtopic: Subtópico (não mais usado, mantido para compatibilidade)
        client: Cliente OpenAI
        api_key: Chave da API
        model: Modelo a ser usado
        topic_summary: Resumo do tópico principal
        related_summary: Resumo do tópico relacionado
    """
    logger.info(f"[QUESTION_AI] Iniciando geração de pergunta para tópico {topic}")
    
    try:
        # Combinar contexto dos resumos
        logger.info("[QUESTION_AI] Combinando contexto dos resumos")
        combined_context = f"""Contexto do tópico principal:
{topic_summary['summary'] if topic_summary else 'Sem resumo disponível'}

Pontos-chave do tópico principal:
{chr(10).join([f"- {point['concept']}: {point['definition']}" for point in topic_summary['key_points']]) if topic_summary else 'Sem pontos-chave disponíveis'}"""

        if related_summary:
            combined_context += f"\n\nTópico relacionado: {related_summary['topic']}\n"
            combined_context += f"Resumo: {related_summary['summary']}\n"
            combined_context += "Pontos-chave:\n"
            combined_context += chr(10).join([f"- {point['concept']}: {point['definition']}" for point in related_summary['key_points']])
        
        prompt = f"""Gere um cenário e uma pergunta sobre {topic}.

O cenário deve ser realista e contextualizado com a prática de gerenciamento de projetos.
A pergunta deve ser clara e objetiva, sem incluir as alternativas.

{combined_context}

Formato esperado:
{{
    "scenario": "Descrição do cenário",
    "question": "Pergunta baseada no cenário"
}}"""

        logger.info("[QUESTION_AI] Enviando requisição para OpenAI")
        response = client.chat.completions.create(
            model=model or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em criar cenários e questões de gerenciamento de projetos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        response_text = response.choices[0].message.content.strip()
        logger.info(f"[QUESTION_AI] Resposta recebida: {response_text[:200]}...")
        
        try:
            question_data = json.loads(response_text)
            logger.info("[QUESTION_AI] JSON decodificado com sucesso")
        except json.JSONDecodeError:
            logger.error(f"[QUESTION_AI] Erro ao decodificar JSON: {response_text}")
            return None

        if not isinstance(question_data, dict):
            logger.error(f"[QUESTION_AI] Formato inválido: {question_data}")
            return None

        required_fields = ["scenario", "question"]
        if not all(field in question_data for field in required_fields):
            logger.error(f"[QUESTION_AI] Campos ausentes: {question_data}")
            return None

        if not all(isinstance(question_data[field], str) for field in required_fields):
            logger.error(f"[QUESTION_AI] Tipos inválidos: {question_data}")
            return None

        question_data["full_question"] = f"{question_data['scenario']}\n\n{question_data['question']}"
        question_data["prompt"] = prompt
        question_data["raw_response"] = response_text
        
        logger.info("[QUESTION_AI] Questão gerada com sucesso")
        return question_data

    except Exception as e:
        logger.error(f"[QUESTION_AI] Erro ao gerar questão: {str(e)}")
        return None

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
    
    Args:
        question_data: Dados da pergunta gerada
        topic: Tópico principal
        subtopic: Subtópico (não mais usado, mantido para compatibilidade)
        client: Cliente OpenAI
        api_key: Chave da API
        model: Modelo a ser usado
        topic_summary: Resumo do tópico principal
        related_summary: Resumo do tópico relacionado
    """
    logger.info(f"[ANSWER_AI] Iniciando geração de resposta para tópico {topic}")
    
    try:
        # Combinar contexto dos resumos
        logger.info("[ANSWER_AI] Combinando contexto dos resumos")
        combined_context = f"""Contexto do tópico principal:
{topic_summary['summary'] if topic_summary else 'Sem resumo disponível'}

Pontos-chave do tópico principal:
{chr(10).join([f"- {point['concept']}: {point['definition']}" for point in topic_summary['key_points']]) if topic_summary else 'Sem pontos-chave disponíveis'}"""

        if related_summary:
            combined_context += f"\n\nTópico relacionado: {related_summary['topic']}\n"
            combined_context += f"Resumo: {related_summary['summary']}\n"
            combined_context += "Pontos-chave:\n"
            combined_context += chr(10).join([f"- {point['concept']}: {point['definition']}" for point in related_summary['key_points']])
        
        prompt = f"""Analise o seguinte cenário e pergunta sobre {topic}:

{question_data['full_question']}

{combined_context}

Gere uma resposta detalhada que inclua:
1. A resposta correta
2. Uma justificativa completa explicando por que esta é a resposta correta
3. Referências específicas ao PMBOK e boas práticas de gerenciamento de projetos
4. Exemplos práticos que ajudem a entender o conceito

A resposta DEVE seguir EXATAMENTE este formato JSON:
{{
    "correct_answer": "Texto da resposta correta",
    "justification": "Explicação detalhada de por que esta é a resposta correta",
    "pmbok_references": ["Referência 1", "Referência 2"],
    "practical_examples": ["Exemplo 1", "Exemplo 2"]
}}"""

        logger.info("[ANSWER_AI] Enviando requisição para OpenAI")
        response = client.chat.completions.create(
            model=model or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos com profundo conhecimento do PMBOK e certificação PMP."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        response_text = response.choices[0].message.content.strip()
        logger.info(f"[ANSWER_AI] Resposta recebida: {response_text[:200]}...")
        
        try:
            answer_data = json.loads(response_text)
            logger.info("[ANSWER_AI] JSON decodificado com sucesso")
        except json.JSONDecodeError:
            logger.error(f"[ANSWER_AI] Erro ao decodificar JSON: {response_text}")
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
            if expected_type == list and not answer_data[field]:
                logger.error(f"[ANSWER_AI] Lista vazia não permitida para {field}")
                return None

        for field in ["pmbok_references", "practical_examples"]:
            if not all(isinstance(item, str) for item in answer_data[field]):
                logger.error(f"[ANSWER_AI] Itens inválidos na lista {field}")
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
    topic_summary: Dict[str, Any] = None,
    related_summary: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Gera distratores baseados na pergunta e resposta correta.
    Esta é a função atual para geração de distratores.
    
    Args:
        question_data: Dados da pergunta gerada
        answer_data: Dados da resposta gerada
        topic: Tópico principal
        subtopic: Subtópico (não mais usado, mantido para compatibilidade)
        client: Cliente OpenAI
        api_key: Chave da API
        model: Modelo a ser usado
        topic_summary: Resumo do tópico principal
        related_summary: Resumo do tópico relacionado
    """
    logger.info(f"[DISTRACTORS] Iniciando geração de distratores para tópico {topic}")
    
    try:
        # Combinar contexto dos resumos
        logger.info("[DISTRACTORS] Combinando contexto dos resumos")
        combined_context = f"""Contexto do tópico principal:
{topic_summary['summary'] if topic_summary else 'Sem resumo disponível'}

Pontos-chave do tópico principal:
{chr(10).join([f"- {point['concept']}: {point['definition']}" for point in topic_summary['key_points']]) if topic_summary else 'Sem pontos-chave disponíveis'}"""

        if related_summary:
            combined_context += f"\n\nTópico relacionado: {related_summary['topic']}\n"
            combined_context += f"Resumo: {related_summary['summary']}\n"
            combined_context += "Pontos-chave:\n"
            combined_context += chr(10).join([f"- {point['concept']}: {point['definition']}" for point in related_summary['key_points']])

        correct_answer_length = len(answer_data['correct_answer'].split())
        allowed_difference = max(3, int(correct_answer_length * 0.3))
        min_length = max(10, correct_answer_length - allowed_difference)
        max_length = correct_answer_length + allowed_difference

        prompt = f"""Analise o seguinte cenário, pergunta e resposta correta sobre {topic}:

Cenário e Pergunta:
{question_data['full_question']}

Resposta Correta:
{answer_data['correct_answer']}

Justificativa da Resposta:
{answer_data['justification']}

{combined_context}

Gere 3 alternativas incorretas (distratores) que devem:
1. Ser plausíveis e relacionadas ao contexto
2. Parecer corretas à primeira vista
3. Ter o mesmo nível de complexidade da resposta correta
4. Ser diferentes entre si
5. Não serem obviamente incorretas
6. Ter entre {min_length} e {max_length} palavras (a resposta correta tem {correct_answer_length} palavras, permitindo uma diferença de {allowed_difference} palavras)

Formato esperado:
[
    "Primeira alternativa incorreta",
    "Segunda alternativa incorreta",
    "Terceira alternativa incorreta"
]"""

        logger.info("[DISTRACTORS] Enviando requisição para OpenAI")
        response = client.chat.completions.create(
            model=model or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em criar alternativas plausíveis para questões de gerenciamento de projetos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        response_text = response.choices[0].message.content.strip()
        logger.info(f"[DISTRACTORS] Resposta recebida: {response_text[:200]}...")
        
        try:
            distractors = json.loads(response_text)
            logger.info("[DISTRACTORS] JSON decodificado com sucesso")
        except json.JSONDecodeError:
            logger.error(f"[DISTRACTORS] Erro ao decodificar JSON: {response_text}")
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

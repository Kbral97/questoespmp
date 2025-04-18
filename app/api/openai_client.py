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

def generate_questions(
    topic: str,
    num_questions: int,
    model: str = None,
    api_key: str = None,
    relevant_chunks: List[str] = None,
    progress_callback=None
) -> List[Dict[str, Any]]:
    """Gera questões sobre um tópico específico"""
    client = get_openai_client(api_key)
    questions = []
    
    for i in range(num_questions):
        if progress_callback:
            progress_callback(i + 1, num_questions)
        
        question = generate_question_with_ai(topic, relevant_chunks, client, api_key, model)
        if question:
            questions.append(question)
    
    return questions

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
    required_fields = ['question', 'answer', 'distractors']
    for field in required_fields:
        if field not in question or not question[field]:
            return False
    
    if len(question['distractors']) < 3:
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

def generate_questions_with_specialized_models(
    topic: str,
    num_questions: int,
    api_key: str,
    num_subtopics: int = 1,
    callback=None,
    question_model=None,
    answer_model=None,
    distractors_model=None
) -> List[Dict[str, Any]]:
    """Gera questões usando modelos especializados"""
    client = get_openai_client(api_key)
    questions = []
    
    # Gerar subtópicos
    subtopics = generate_subtopics(topic, num_subtopics)
    
    for subtopic in subtopics:
        for i in range(num_questions // num_subtopics):
            if callback:
                callback(i + 1, num_questions)
            
            # Gerar questão
            question = generate_question_with_ai(
                subtopic,
                None,
                client,
                api_key,
                question_model
            )
            
            if question:
                # Gerar resposta
                answer = generate_answer_with_ai(
                    question['question'],
                    None,
                    client,
                    api_key,
                    answer_model
                )
                
                if answer:
                    question['answer'] = answer
                    
                    # Gerar distratores
                    distractors = generate_distractors_with_ai(
                        question['question'],
                        answer,
                        None,
                        client,
                        api_key,
                        distractors_model
                    )
                    
                    if distractors:
                        question['distractors'] = distractors
                        questions.append(question)
    
    return questions

def generate_subtopics(topic: str, num_subtopics: int) -> List[str]:
    """Gera subtópicos para um tópico principal"""
    prompt = f"""
    Gere {num_subtopics} subtópicos específicos para o tópico: {topic}
    Retorne apenas uma lista de subtópicos, um por linha.
    """
    
    client = get_openai_client()
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos."},
                {"role": "user", "content": prompt}
            ]
        )
        subtopics = response.choices[0].message.content.strip().split('\n')
        return [s.strip() for s in subtopics if s.strip()]
    except Exception as e:
        logger.error(f"Erro ao gerar subtópicos: {str(e)}")
        return [topic]

def generate_question_with_ai(topic: str, context: str, client: OpenAI, api_key: str, model: str = None) -> Optional[Dict]:
    """Gera uma questão usando IA"""
    prompt = f"""
    Gere uma questão de múltipla escolha sobre o tópico: {topic}
    A questão deve ser clara, concisa e relevante para o exame PMP.
    Não inclua a resposta ou distratores.
    """
    
    if context:
        prompt = get_enhanced_prompt(prompt, context)
    
    try:
        response = client.chat.completions.create(
            model=model or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos."},
                {"role": "user", "content": prompt}
            ]
        )
        return {'question': response.choices[0].message.content.strip()}
    except Exception as e:
        logger.error(f"Erro ao gerar questão: {str(e)}")
        return None

def generate_answer_with_ai(question: str, context: str, client: OpenAI, api_key: str, model: str = None) -> Optional[Dict]:
    """Gera uma resposta usando IA"""
    prompt = f"""
    Gere uma resposta correta para a seguinte questão:
    {question}
    A resposta deve ser precisa e bem fundamentada.
    """
    
    if context:
        prompt = get_enhanced_prompt(prompt, context)
    
    try:
        response = client.chat.completions.create(
            model=model or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos."},
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Erro ao gerar resposta: {str(e)}")
        return None

def generate_distractors_with_ai(question: str, correct_answer: str, context: str, client: OpenAI, api_key: str, model: str = "gpt-3.5-turbo") -> tuple:
    """Gera distratores usando IA"""
    prompt = f"""
    Gere 3 distratores (respostas incorretas) para a seguinte questão e resposta correta:
    Questão: {question}
    Resposta correta: {correct_answer}
    Os distratores devem ser plausíveis e relacionados ao tópico.
    """
    
    if context:
        prompt = get_enhanced_prompt(prompt, context)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos."},
                {"role": "user", "content": prompt}
            ]
        )
        distractors = response.choices[0].message.content.strip().split('\n')
        return tuple(d.strip() for d in distractors[:3])
    except Exception as e:
        logger.error(f"Erro ao gerar distratores: {str(e)}")
        return None

def generate_wrong_answers_with_ai(question: str, correct_answer: str, context: str, client: OpenAI, api_key: str, model: str = None) -> Optional[List[str]]:
    """Gera respostas incorretas usando IA"""
    prompt = f"""
    Gere 3 respostas incorretas para a seguinte questão e resposta correta:
    Questão: {question}
    Resposta correta: {correct_answer}
    As respostas incorretas devem ser plausíveis e relacionadas ao tópico.
    """
    
    if context:
        prompt = get_enhanced_prompt(prompt, context)
    
    try:
        response = client.chat.completions.create(
            model=model or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos."},
                {"role": "user", "content": prompt}
            ]
        )
        wrong_answers = response.choices[0].message.content.strip().split('\n')
        return [a.strip() for a in wrong_answers[:3]]
    except Exception as e:
        logger.error(f"Erro ao gerar respostas incorretas: {str(e)}")
        return None 
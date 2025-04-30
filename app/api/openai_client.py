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
    subtopic: str,
    num_questions: int,
    client: Any,
    api_key: str,
    model: str = None
) -> List[Dict[str, Any]]:
    """Gera múltiplas questões usando três IAs especializadas"""
    try:
        questions = []
        for i in range(num_questions):
            # 1. Primeira IA: Gera o cenário e a pergunta
            question_data = generate_question_with_ai(
                topic=topic,
                subtopic=subtopic,
                client=client,
                api_key=api_key,
                model=model
            )
            if not question_data:
                logger.error(f"Falha ao gerar cenário e pergunta {i+1}")
                continue

            # 2. Segunda IA: Gera a resposta correta com justificativa
            answer_data = generate_answer_with_ai(
                question_data=question_data,
                topic=topic,
                subtopic=subtopic,
                client=client,
                api_key=api_key,
                model=model
            )
            if not answer_data:
                logger.error(f"Falha ao gerar resposta e justificativa para questão {i+1}")
                continue

            # 3. Terceira IA: Gera os distratores
            distractors = generate_distractors(
                question_data=question_data,
                answer_data=answer_data,
                topic=topic,
                subtopic=subtopic,
                client=client,
                api_key=api_key,
                model=model
            )
            if not distractors:
                logger.error(f"Falha ao gerar distratores para questão {i+1}")
                continue

            # Montar questão completa
            question = {
                "scenario": question_data["scenario"],
                "question": question_data["question"],
                "full_question": question_data["full_question"],
                "options": {
                    "A": distractors[0],
                    "B": distractors[1],
                    "C": distractors[2],
                    "D": answer_data["correct_answer"]
                },
                "correct_answer": "D",
                "justification": answer_data["justification"],
                "pmbok_references": answer_data["pmbok_references"],
                "practical_examples": answer_data["practical_examples"],
                "topic": topic,
                "subtopic": subtopic,
                "relevant_chunks": {
                    "question": question_data["relevant_chunks"],
                    "answer": answer_data["relevant_chunks"]
                }
            }
            questions.append(question)

        return questions

    except Exception as e:
        logger.error(f"Erro ao gerar questões: {str(e)}")
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
            question, question_prompt, question_chunks = generate_question_with_ai(
                subtopic,
                None,
                client,
                api_key,
                question_model
            )
            
            if question:
                # Gerar resposta
                answer, answer_prompt, answer_chunks = generate_answer_with_ai(
                    question['question'],
                    subtopic,
                    answer_chunks,
                    client,
                    api_key,
                    answer_model
                )
                
                if answer:
                    question['answer'] = answer
                    question['answer_prompt'] = answer_prompt
                    question['answer_chunks'] = answer_chunks
                    
                    # Gerar distratores
                    distractors, distractors_prompt, distractors_chunks = generate_distractors(
                        question_data=question,
                        answer_data=answer,
                        topic=topic,
                        subtopic=subtopic,
                        client=client,
                        api_key=api_key,
                        model=distractors_model
                    )
                    
                    if distractors:
                        question['distractors'] = distractors
                        question['distractors_prompt'] = distractors_prompt
                        question['distractors_chunks'] = distractors_chunks
                        question['question_prompt'] = question_prompt
                        question['question_chunks'] = question_chunks
                        question['topic'] = topic
                        question['subtopic'] = subtopic
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

def find_relevant_chunks(query: str, top_k: int = 3) -> List[Dict]:
    """Encontra chunks relevantes no banco de dados baseado na similaridade semântica"""
    try:
        db = DatabaseManager()
        chunks = db.get_all_chunks()
        
        if not chunks:
            return []
        
        # Extrair textos para comparação
        texts = [chunk['content'] for chunk in chunks]
        texts.append(query)
        
        # Criar vetorizador TF-IDF
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(texts)
        
        # Calcular similaridade
        query_vector = tfidf_matrix[-1]
        similarities = cosine_similarity(query_vector, tfidf_matrix[:-1])[0]
        
        # Ordenar por similaridade
        indices = np.argsort(similarities)[::-1][:top_k]
        
        return [chunks[i] for i in indices]
    except Exception as e:
        logger.error(f"Erro ao buscar chunks relevantes: {str(e)}")
        return []

def generate_question_with_ai(
    topic: str,
    subtopic: str,
    client: Any,
    api_key: str,
    model: str = None
) -> Dict[str, str]:
    """Gera apenas o cenário e a pergunta usando IA"""
    try:
        # Buscar chunks relevantes para o tópico
        topic_query = f"{topic} {subtopic}"
        relevant_chunks = find_relevant_chunks(topic_query)
        
        prompt = f"""Gere um cenário e uma pergunta sobre {topic} - {subtopic}.

O cenário deve ser realista e contextualizado com a prática de gerenciamento de projetos.
A pergunta deve ser clara e objetiva, sem incluir as alternativas.

Contexto relevante do PMBOK:
{chr(10).join([chunk['content'] for chunk in relevant_chunks])}

Formato esperado:
{{
    "scenario": "Descrição do cenário",
    "question": "Pergunta baseada no cenário"
}}"""

        response = client.chat.completions.create(
            model=model or "gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Você é um especialista em criar cenários e questões de gerenciamento de projetos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        # Extrair e validar resposta
        response_text = response.choices[0].message.content.strip()
        try:
            question_data = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error(f"Erro ao decodificar JSON da resposta: {response_text}")
            return None

        # Validar formato
        if not isinstance(question_data, dict):
            logger.error(f"Formato de resposta inválido: {question_data}")
            return None

        # Validar campos obrigatórios
        required_fields = ["scenario", "question"]
        if not all(field in question_data for field in required_fields):
            logger.error(f"Campos obrigatórios ausentes: {question_data}")
            return None

        # Validar tipos dos campos
        if not all(isinstance(question_data[field], str) for field in required_fields):
            logger.error(f"Tipos de campos inválidos: {question_data}")
            return None

        # Combinar cenário e pergunta
        question_data["full_question"] = f"{question_data['scenario']}\n\n{question_data['question']}"
        question_data["relevant_chunks"] = relevant_chunks
        
        return question_data

    except Exception as e:
        logger.error(f"Erro ao gerar questão: {str(e)}")
        return None

def generate_answer_with_ai(
    question_data: Dict[str, str],
    topic: str,
    subtopic: str,
    client: Any,
    api_key: str,
    model: str = None
) -> Dict[str, Any]:
    """Gera a resposta correta com justificativa detalhada"""
    try:
        # Buscar chunks relevantes para a pergunta
        question_query = f"{question_data['full_question']} {topic} {subtopic}"
        relevant_chunks = find_relevant_chunks(question_query)
        
        prompt = f"""Analise o seguinte cenário e pergunta sobre {topic} - {subtopic}:

{question_data['full_question']}

Contexto relevante do PMBOK:
{chr(10).join([chunk['content'] for chunk in relevant_chunks])}

Gere uma resposta detalhada que inclua:
1. A resposta correta
2. Uma justificativa completa explicando por que esta é a resposta correta
3. Referências específicas ao PMBOK e boas práticas de gerenciamento de projetos
4. Exemplos práticos que ajudem a entender o conceito

Formato esperado:
{{
    "correct_answer": "Texto da resposta correta",
    "justification": "Explicação detalhada de por que esta é a resposta correta",
    "pmbok_references": ["Referência 1", "Referência 2", ...],
    "practical_examples": ["Exemplo 1", "Exemplo 2", ...]
}}"""

        response = client.chat.completions.create(
            model=model or "gpt-4",
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos com profundo conhecimento do PMBOK e certificação PMP."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )

        # Extrair e validar resposta
        response_text = response.choices[0].message.content.strip()
        try:
            answer_data = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error(f"Erro ao decodificar JSON da resposta: {response_text}")
            return None

        # Validar formato
        if not isinstance(answer_data, dict):
            logger.error(f"Formato de resposta inválido: {answer_data}")
            return None

        # Validar campos obrigatórios
        required_fields = ["correct_answer", "justification", "pmbok_references", "practical_examples"]
        if not all(field in answer_data for field in required_fields):
            logger.error(f"Campos obrigatórios ausentes: {answer_data}")
            return None

        # Validar tipos dos campos
        if not isinstance(answer_data["correct_answer"], str) or \
           not isinstance(answer_data["justification"], str) or \
           not isinstance(answer_data["pmbok_references"], list) or \
           not isinstance(answer_data["practical_examples"], list):
            logger.error(f"Tipos de campos inválidos: {answer_data}")
            return None

        answer_data["relevant_chunks"] = relevant_chunks
        return answer_data

    except Exception as e:
        logger.error(f"Erro ao gerar resposta: {str(e)}")
        return None

def generate_distractors(
    question_data: Dict[str, str],
    answer_data: Dict[str, Any],
    topic: str,
    subtopic: str,
    client: Any,
    api_key: str,
    model: str = None
) -> List[str]:
    """Gera distratores baseados na pergunta e resposta correta"""
    try:
        # Buscar chunks relevantes para a resposta
        answer_query = f"{answer_data['correct_answer']} {answer_data['justification']} {topic} {subtopic}"
        relevant_chunks = find_relevant_chunks(answer_query)
        
        # Calcular o tamanho da resposta correta e a diferença permitida
        correct_answer_length = len(answer_data['correct_answer'].split())
        allowed_difference = max(3, int(correct_answer_length * 0.3))  # Maior entre 3 palavras ou 30%
        min_length = correct_answer_length - allowed_difference
        max_length = correct_answer_length + allowed_difference
        
        prompt = f"""Analise o seguinte cenário, pergunta e resposta correta sobre {topic} - {subtopic}:

Cenário e Pergunta:
{question_data['full_question']}

Resposta Correta:
{answer_data['correct_answer']}

Justificativa da Resposta:
{answer_data['justification']}

Contexto relevante do PMBOK:
{chr(10).join([chunk['content'] for chunk in relevant_chunks])}

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

        response = client.chat.completions.create(
            model=model or "gpt-4",
            messages=[
                {"role": "system", "content": "Você é um especialista em criar alternativas plausíveis para questões de gerenciamento de projetos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )

        # Extrair e validar resposta
        response_text = response.choices[0].message.content.strip()
        try:
            distractors = json.loads(response_text)
        except json.JSONDecodeError:
            logger.error(f"Erro ao decodificar JSON da resposta: {response_text}")
            return None

        # Validar formato
        if not isinstance(distractors, list) or len(distractors) != 3:
            logger.error(f"Formato de resposta inválido: {distractors}")
            return None

        # Validar tipos dos campos
        if not all(isinstance(d, str) for d in distractors):
            logger.error(f"Tipos de campos inválidos: {distractors}")
            return None

        # Validar que os distratores são diferentes entre si e da resposta correta
        all_options = distractors + [answer_data['correct_answer']]
        if len(set(all_options)) != 4:
            logger.error(f"Distratores duplicados ou iguais à resposta correta: {distractors}")
            return None

        # Validar tamanho dos distratores
        for distractor in distractors:
            distractor_length = len(distractor.split())
            if distractor_length < min_length or distractor_length > max_length:
                logger.error(f"Distrator com tamanho fora do intervalo permitido ({min_length}-{max_length} palavras): {distractor}")
                return None

        return distractors

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
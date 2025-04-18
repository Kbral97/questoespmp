#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OpenAI Client para geração de questões PMP
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
from questoespmp2.database.db_manager import DatabaseManager
import random

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Definir diretórios base
BASE_DIR = Path(__file__).parent.parent.parent
TRAINING_DATA_DIR = BASE_DIR / "data" / "training"
MODELS_DIR = BASE_DIR / "data" / "models"

# Criar diretórios se não existirem
TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

def get_training_file_path(filename):
    """Retorna o caminho completo para um arquivo de treinamento."""
    return TRAINING_DATA_DIR / filename

def get_model_file_path(model_id):
    """Retorna o caminho completo para um arquivo de modelo fine-tuned."""
    return MODELS_DIR / f"{model_id}.json"

def save_training_data(data, filename):
    """Salva dados de treinamento em um arquivo JSON."""
    file_path = get_training_file_path(filename)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Dados de treinamento salvos em {file_path}")
        return str(file_path)
    except Exception as e:
        logger.error(f"Erro ao salvar dados de treinamento: {e}")
        raise

def save_model_info(model_id, model_info):
    """Salva informações sobre um modelo fine-tuned."""
    file_path = get_model_file_path(model_id)
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(model_info, f, ensure_ascii=False, indent=2)
        logger.info(f"Informações do modelo salvas em {file_path}")
        return str(file_path)
    except Exception as e:
        logger.error(f"Erro ao salvar informações do modelo: {e}")
        raise

def load_model_info(model_id):
    """Carrega informações sobre um modelo fine-tuned."""
    file_path = get_model_file_path(model_id)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar informações do modelo: {e}")
        return None

def list_available_models():
    """Lista todos os modelos fine-tuned disponíveis."""
    try:
        models = []
        for file in MODELS_DIR.glob("*.json"):
            model_info = load_model_info(file.stem)
            if model_info:
                models.append(model_info)
        return models
    except Exception as e:
        logger.error(f"Erro ao listar modelos: {e}")
        return []

def get_openai_client(api_key=None):
    """
    Obtém um cliente OpenAI configurado com a chave API fornecida ou a chave padrão do ambiente.
    
    Args:
        api_key (str, optional): Chave de API OpenAI. Se não for fornecida, tenta usar OPENAI_API_KEY do ambiente.
        
    Returns:
        OpenAI: Cliente OpenAI configurado.
        
    Raises:
        ValueError: Se nenhuma chave API válida for encontrada.
    """
    if not api_key:
        # Tenta obter do ambiente
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        raise ValueError("API key não encontrada. Forneça uma chave de API ou defina a variável de ambiente OPENAI_API_KEY.")
        
    return OpenAI(api_key=api_key)

def find_relevant_training_data(query: str, top_k: int = 3) -> List[Dict]:
    """
    Encontra os arquivos de treinamento mais relevantes para uma consulta.
    
    Args:
        query (str): Texto da consulta
        top_k (int): Número de resultados mais relevantes a retornar
        
    Returns:
        List[Dict]: Lista de dicionários com informações dos arquivos relevantes
    """
    try:
        # Listar todos os arquivos de treinamento
        training_files = list(TRAINING_DATA_DIR.glob("*.json"))
        if not training_files:
            logger.warning("Nenhum arquivo de treinamento encontrado")
            return []
            
        # Carregar conteúdo dos arquivos
        documents = []
        file_info = []
        for file in training_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Extrair texto das questões
                    text = " ".join([q.get('question', '') for q in data])
                    documents.append(text)
                    file_info.append({
                        'path': str(file),
                        'name': file.name,
                        'questions_count': len(data)
                    })
            except Exception as e:
                logger.error(f"Erro ao ler arquivo {file}: {e}")
                continue
                
        if not documents:
            return []
            
        # Criar vetorizador TF-IDF
        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(documents)
        
        # Calcular similaridade
        query_vector = vectorizer.transform([query])
        similarities = cosine_similarity(query_vector, tfidf_matrix).flatten()
        
        # Ordenar por similaridade
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        # Retornar informações dos arquivos mais relevantes
        relevant_files = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Só incluir se tiver alguma relevância
                file_info[idx]['similarity'] = float(similarities[idx])
                relevant_files.append(file_info[idx])
                
        return relevant_files
        
    except Exception as e:
        logger.error(f"Erro ao buscar arquivos relevantes: {e}")
        return []

def get_enhanced_prompt(base_prompt: str, relevant_files: List[Dict]) -> str:
    """
    Melhora o prompt base usando informações dos arquivos relevantes.
    
    Args:
        base_prompt (str): Prompt original
        relevant_files (List[Dict]): Lista de arquivos relevantes
        
    Returns:
        str: Prompt melhorado
    """
    try:
        # Carregar conteúdo dos arquivos relevantes
        context = []
        for file_info in relevant_files:
            try:
                with open(file_info['path'], 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Extrair algumas questões relevantes
                    questions = [q.get('question', '') for q in data[:3]]
                    context.extend(questions)
            except Exception as e:
                logger.error(f"Erro ao ler arquivo {file_info['path']}: {e}")
                continue
                
        if not context:
            return base_prompt
            
        # Construir prompt melhorado
        enhanced_prompt = f"""Com base no seguinte contexto e no prompt fornecido, gere questões de certificação PMP:

Contexto (exemplos de questões relevantes):
{chr(10).join(f'- {q}' for q in context)}

Prompt original:
{base_prompt}

Por favor, gere questões que:
1. Sigam o mesmo estilo e formato das questões de exemplo
2. Mantenham a consistência com o contexto fornecido
3. Abordem os mesmos conceitos e temas
4. Tenham o mesmo nível de detalhamento e complexidade

Lembre-se de incluir:
- Pergunta clara e objetiva
- 4 opções de resposta (A, B, C, D)
- Resposta correta
- Explicação detalhada da resposta
- Referência ao PMBOK quando aplicável"""
        
        return enhanced_prompt
        
    except Exception as e:
        logger.error(f"Erro ao melhorar prompt: {e}")
        return base_prompt

def generate_questions(
    topic: str,
    num_questions: int,
    model: str = None,
    api_key: str = None,
    relevant_chunks: List[str] = None,
    progress_callback=None
) -> List[Dict[str, Any]]:
    """
    Gera questões sobre um tópico específico.
    """
    try:
        # Mapear ID do modelo para ID da API
        model = map_model_id_to_api(model)
        if not model:
            model = "gpt-3.5-turbo"  # Modelo padrão
            
        # Configurar cliente OpenAI
        client = get_openai_client(api_key)
        
        logger.info(f"Gerando {num_questions} questões sobre {topic}")
        
        # Atualizar progresso para 10%
        if progress_callback:
            progress_callback(10, "Iniciando geração de questões...")
            
        # Gerar questões usando modelos especializados
            questions = generate_questions_with_specialized_models(
                topic=topic,
                num_questions=num_questions,
            api_key=api_key,
            callback=progress_callback
            )
            
        if not questions:
            logger.error("Não foi possível gerar questões. Verifique se a API está disponível.")
        if progress_callback:
            progress_callback(0, "Erro: Não foi possível gerar questões")
            return []
            
        # Atualizar progresso para 100%
        if progress_callback:
            progress_callback(100, f"Geradas {len(questions)} questões com sucesso!")
            
        return questions
        
    except Exception as e:
        logger.error(f"Erro ao gerar questões: {str(e)}")
        if progress_callback:
            progress_callback(0, f"Erro: {str(e)}")
        return []

def format_training_data(questions):
    """
    Formata os dados de treinamento para o formato esperado pela API OpenAI.
    
    Args:
        questions (list): Lista de dicionários de questões
        
    Returns:
        list: Dados formatados para fine-tuning
    """
    formatted_data = []
    
    for q in questions:
        # Construir as opções formatadas
        options_text = ""
        for i, option in enumerate(q.get("options", [])):
            options_text += f"\n{chr(65+i)}. {option}"
        
        # Construir a mensagem completa da questão
        question_text = f"{q.get('question', '')}\n{options_text}"
        
        # Construir a resposta
        correct_idx = q.get("correct_answer", 0)
        correct_letter = chr(65 + correct_idx) if 0 <= correct_idx <= 3 else "A"
        explanation = q.get("explanation", "")
        answer_text = f"A resposta correta é {correct_letter}. {explanation}"
        
        # Adicionar à lista formatada
        formatted_data.append({
            "messages": [
                {"role": "system", "content": "Você é um especialista em certificação PMP e cria questões de múltipla escolha de alta qualidade."},
                {"role": "user", "content": "Crie uma questão de certificação PMP no formato de múltipla escolha."},
                {"role": "assistant", "content": question_text},
                {"role": "user", "content": "Qual é a resposta correta e por quê?"},
                {"role": "assistant", "content": answer_text}
            ]
        })
    
    return formatted_data

def tune_model(training_data, api_key=None, model_name="gpt-3.5-turbo"):
    """
    Fine-tune an OpenAI model with PMP question examples.
    
    Args:
        training_data (list): List of question dictionaries for training
        api_key (str, optional): OpenAI API key. Defaults to None.
        model_name (str, optional): Base model for fine-tuning. Defaults to "gpt-3.5-turbo".
        
    Returns:
        dict: Information about the fine-tuning job
    """
    try:
        # Obter cliente OpenAI
        client = get_openai_client(api_key)
        
        if not client:
            return {"error": "Nenhuma chave de API fornecida"}
        
        # Log do início do processo
        logger.info(f"Iniciando processo de fine-tuning com {len(training_data)} exemplos")
        
        # Formatar os dados para o formato esperado pela API
        formatted_data = format_training_data(training_data)
        
        # Salvar os dados formatados em um arquivo temporário
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        temp_filename = f"ft_pmp_questions_{timestamp}.jsonl"
        
        with open(temp_filename, "w", encoding="utf-8") as f:
            for item in formatted_data:
                f.write(json.dumps(item) + "\n")
        
        logger.info(f"Dados salvos em arquivo temporário: {temp_filename}")
        
        try:
            # Upload do arquivo para a OpenAI
            with open(temp_filename, "rb") as f:
                upload_response = client.files.create(
                    file=f,
                    purpose="fine-tune"
                )
            
            file_id = upload_response.id
            logger.info(f"Arquivo enviado com sucesso. ID: {file_id}")
            
            # Aguardar processamento do arquivo
            wait_time = 0
            max_wait = 60  # segundos
            while wait_time < max_wait:
                file_info = client.files.retrieve(file_id)
                if file_info.status == "processed":
                    break
                time.sleep(2)
                wait_time += 2
                logger.info(f"Aguardando processamento do arquivo: {wait_time}s passados")
            
            # Criar job de fine-tuning
            response = client.fine_tuning.jobs.create(
                training_file=file_id,
                model=model_name,
                suffix=f"pmp-questions-{timestamp}"
            )
            
            # Extrair informações do job
            job_id = response.id
            status = response.status
            
            logger.info(f"Job de fine-tuning criado com sucesso. ID: {job_id}, Status: {status}")
            
            # Retornar informações do job
            return {
                "job_id": job_id,
                "status": status,
                "estimated_completion": "2-3 horas (dependendo da fila da OpenAI)",
                "base_model": model_name,
                "training_examples": len(training_data),
                "file_id": file_id
            }
            
        except Exception as e:
            logger.error(f"Erro na API OpenAI: {e}")
            # Remover arquivo temporário em caso de erro
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
            return {"error": str(e)}
        
    except Exception as e:
        logger.error(f"Erro no fine-tuning do modelo: {e}")
        return {"error": str(e)}

def get_tuning_status(job_id, api_key=None):
    """
    Get the status of a fine-tuning job.
    
    Args:
        job_id (str): The ID of the fine-tuning job
        api_key (str, optional): OpenAI API key. Defaults to None.
        
    Returns:
        dict: Information about the fine-tuning job status
    """
    try:
        # Obter cliente OpenAI
        client = get_openai_client(api_key)
        
        if not client:
            return {"error": "Nenhuma chave de API fornecida"}
        
        # Log da verificação
        logger.info(f"Verificando status do job de fine-tuning {job_id}")
        
        # Obter status do job
        job = client.fine_tuning.jobs.retrieve(job_id)
        
        # Extrair informações relevantes
        status = job.status
        created_at = job.created_at
        finished_at = job.finished_at
        
        # Calcular progresso (estimativa)
        progress = "0%"
        if status == "running":
            # Estimar progresso baseado no tempo decorrido
            # Suponha que leva em média 2 horas para completar
            elapsed_seconds = time.time() - created_at
            estimated_total_seconds = 2 * 60 * 60  # 2 horas em segundos
            progress_pct = min(95, (elapsed_seconds / estimated_total_seconds) * 100)
            progress = f"{int(progress_pct)}%"
        elif status in ["succeeded", "failed", "cancelled"]:
            progress = "100%"
        
        # Obter nome do modelo se disponível
        fine_tuned_model = job.fine_tuned_model if status == "succeeded" else None
        
        # Retornar informações do status
        return {
            "job_id": job_id,
            "status": status,
            "progress": progress,
            "created_at": datetime.fromtimestamp(created_at).isoformat(),
            "finished_at": datetime.fromtimestamp(finished_at).isoformat() if finished_at else None,
            "model": fine_tuned_model
        }
        
    except Exception as e:
        logger.error(f"Erro ao verificar status do fine-tuning: {e}")
        return {"error": str(e)}

def validate_question_quality(question: Dict) -> bool:
    """
    Valida a qualidade de uma questão gerada.
    
    Args:
        question: Dicionário com dados da questão
        
    Returns:
        bool: True se a questão passou na validação, False caso contrário
    """
    try:
        # Verificar se a pergunta não está vazia
        if not question.get('question'):
            logger.warning("Questão rejeitada: pergunta vazia")
            return False
            
        # Verificar se existem 4 opções
        if len(question.get('options', [])) != 4:
            logger.warning(f"Questão rejeitada: número incorreto de opções ({len(question.get('options', []))})")
            return False
            
        # Verificar se a resposta correta é uma letra válida (A, B, C ou D)
        correct_answer = question.get('correct_answer', '')
        if correct_answer not in ['A', 'B', 'C', 'D']:
            logger.warning(f"Questão rejeitada: resposta correta inválida ({correct_answer})")
            return False
            
        # Verificar se há explicação
        if not question.get('explanation'):
            logger.warning("Questão rejeitada: sem explicação")
            return False
            
        return True
    except Exception as e:
        logger.error(f"Erro ao validar questão: {e}")
        return False

def map_model_id_to_api(model_id: str) -> str:
    """Mapeia IDs internos de modelos para IDs da API OpenAI."""
    if not model_id:
        return None
        
    # Mapeamento de modelos padrão
    model_mapping = {
        "default_gpt35": "gpt-3.5-turbo",
        "default_gpt4": "gpt-4"
    }
    
    # Se o modelo já estiver no formato da API (ft:... ou gpt-...), retornar como está
    if model_id.startswith("ft:") or model_id.startswith("gpt-"):
        return model_id
    
    # Se for um modelo padrão, retornar o mapeamento
    return model_mapping.get(model_id, model_id)

def process_openai_response(response_text):
    """Processa a resposta da API OpenAI, removendo marcadores Markdown e extraindo o JSON."""
    logger.debug(f"Texto da resposta: {response_text}")
    
    # Remover marcadores Markdown ```json e ``` se presentes
    if response_text.startswith("```json"):
        response_text = response_text.replace("```json", "", 1)
        if response_text.endswith("```"):
            response_text = response_text[:-3]
    elif response_text.startswith("```"):
        response_text = response_text.replace("```", "", 1)
        if response_text.endswith("```"):
            response_text = response_text[:-3]
    
    # Limpar espaços em branco no início e fim
    response_text = response_text.strip()
    
    try:
        # Tenta converter para JSON
        json_data = json.loads(response_text)
        return json_data
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON da resposta: {e}")
        logger.error(f"Texto que falhou: {response_text}")
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
    """
    Gera questões usando modelos especializados para cada componente.
    Cada questão requer 3 chamadas à API:
    1. Geração da pergunta
    2. Geração da resposta correta
    3. Geração dos distratores
    
    Args:
        topic (str): Tópico principal
        num_questions (int): Número de questões para gerar
        api_key (str, optional): Chave da API OpenAI
        num_subtopics (int): Número de subtópicos a gerar (default: 1)
        callback (callable, optional): Função de callback para atualizar progresso
        question_model (str): Modelo para gerar perguntas
        answer_model (str): Modelo para gerar respostas
        distractors_model (str): Modelo para gerar distratores
        
    Returns:
        list: Lista de questões geradas
    """
    try:
        # Mapear IDs dos modelos para IDs da API
        question_model = map_model_id_to_api(question_model)
        answer_model = map_model_id_to_api(answer_model)
        distractors_model = map_model_id_to_api(distractors_model)
        
        # Verificar se todos os modelos necessários estão disponíveis
        if not all([question_model, answer_model, distractors_model]):
            logger.error("Modelos necessários não fornecidos")
            if callback:
                callback(0, "Erro: Não foi possível gerar questões")
            return []
            
        # Gerar subtópicos
        subtopics = generate_subtopics(topic, num_subtopics)
        logger.info(f"Subtópicos gerados: {subtopics}")
            
        # Obter chunks relevantes do banco de dados
        db = DatabaseManager()
        relevant_chunks = db.find_most_relevant_chunks(topic, num_chunks=3)
        if not relevant_chunks:
            logger.error("Nenhum dado relevante encontrado no banco de dados")
            return []
            
        # Preparar contexto para os prompts
        context = ""
        for chunk in relevant_chunks:
            context += f"\nTrecho do arquivo {chunk['file_name']}:\n{chunk['raw_text']}\n"
            
        # Distribuir questões entre os subtópicos
        questions_per_subtopic = num_questions // len(subtopics)
        remaining_questions = num_questions % len(subtopics)
        
        # Gerar questões
        questions = []
        current_subtopic_index = 0
        questions_for_current_subtopic = questions_per_subtopic + (1 if remaining_questions > 0 else 0)
        
        for question_index in range(num_questions):
            try:
                # Verificar se precisamos mudar para o próximo subtópico
                if questions_for_current_subtopic == 0:
                    current_subtopic_index += 1
                    remaining_questions = max(0, remaining_questions - 1)
                    questions_for_current_subtopic = questions_per_subtopic + (1 if remaining_questions > 0 else 0)
                
                current_subtopic = subtopics[current_subtopic_index]
                
                # Atualizar progresso
                if callback:
                    progress = (question_index + 1) / num_questions
                    callback(progress, f"Gerando questão {question_index + 1} de {num_questions} para {current_subtopic}")
                
                # Gerar pergunta e resposta correta
                question_data = generate_question_with_ai(
                    current_subtopic, 
                    context, 
                    get_openai_client(api_key), 
                    api_key,
                    model=question_model
                )
                if not question_data:
                    logger.error(f"Falha ao gerar pergunta {question_index + 1}")
                    continue
                
                # Gerar resposta correta com justificativa
                answer_data = generate_answer_with_ai(
                    question_data['question'],
                    context,
                    get_openai_client(api_key),
                    api_key,
                    model=answer_model
                )
                if not answer_data:
                    logger.error(f"Falha ao gerar resposta para questão {question_index + 1}")
                    continue
                
                correct_answer, explanation = answer_data
                
                # Gerar distratores
                distractors, _ = generate_distractors_with_ai(
                    question_data['question'],
                    correct_answer,
                    context,
                    get_openai_client(api_key),
                    api_key,
                    model=distractors_model
                )
                if not distractors:
                    logger.error(f"Falha ao gerar distratores para questão {question_index + 1}")
                    continue
                
                # Montar questão completa
                options = [correct_answer] + distractors
                
                # Verificar e truncar opções muito longas
                for i in range(len(options)):
                    if len(options[i]) > 200:
                        logger.warning(f"Opção {chr(65+i)} gerada pela API era muito longa, truncando...")
                        options[i] = options[i][:197] + "..."
                
                question = {
                    'question': question_data['question'],
                    'options': options,
                    'correct_answer': 'A',  # Definir sempre como A e depois ajustar após embaralhar
                    'explanation': explanation,
                    'topic': topic,
                    'subtopic': current_subtopic,
                    'difficulty': question_data.get('difficulty', 1)
                }
                
                # Embaralhar opções
                correct_option = options[0]
                random.shuffle(question['options'])
                
                # Atualizar alternativa correta
                correct_index = question['options'].index(correct_option)
                question['correct_answer'] = chr(65 + correct_index)  # A, B, C ou D
                
                # Validar qualidade da questão
                if validate_question_quality(question):
                    questions.append(question)
                    questions_for_current_subtopic -= 1
                    # Salvar no banco de dados
                    try:
                        db.save_question(question)
                    except Exception as e:
                        logger.error(f"Erro ao salvar questão no banco: {e}")
                else:
                    logger.warning(f"Questão {question_index + 1} não passou na validação de qualidade")
            except Exception as e:
                logger.error(f"Erro ao gerar questão {question_index + 1}: {e}")
                continue
        
        # Atualizar progresso final
        if callback:
            callback(1.0, f"Geração concluída: {len(questions)} questões geradas")
                
        logger.info(f"Geração concluída: {len(questions)} questões geradas")
        return questions
            
    except Exception as e:
        logger.error(f"Erro na geração de questões: {e}")
        return []

def generate_subtopics(topic: str, num_subtopics: int) -> List[str]:
    """
    Gera subtópicos para um tópico principal usando a API da OpenAI.
    
    Args:
        topic: Tópico principal
        num_subtopics: Número de subtópicos a gerar
        
    Returns:
        Lista de subtópicos
    """
    try:
        # Mapear tópicos principais do PMBOK para seus subtópicos conhecidos
        known_subtopics = {
            "Gerenciamento da Integração": [
                "Desenvolver o Termo de Abertura do Projeto",
                "Desenvolver o Plano de Gerenciamento do Projeto",
                "Orientar e Gerenciar o Trabalho do Projeto",
                "Gerenciar o Conhecimento do Projeto",
                "Monitorar e Controlar o Trabalho do Projeto",
                "Realizar o Controle Integrado de Mudanças",
                "Encerrar o Projeto ou Fase"
            ],
            "Gerenciamento do Escopo": [
                "Planejar o Gerenciamento do Escopo",
                "Coletar os Requisitos",
                "Definir o Escopo",
                "Criar a EAP",
                "Validar o Escopo",
                "Controlar o Escopo"
            ],
            "Gerenciamento do Cronograma": [
                "Planejar o Gerenciamento do Cronograma",
                "Definir as Atividades",
                "Sequenciar as Atividades",
                "Estimar as Durações das Atividades",
                "Desenvolver o Cronograma",
                "Controlar o Cronograma"
            ],
            "Gerenciamento dos Custos": [
                "Planejar o Gerenciamento dos Custos",
                "Estimar os Custos",
                "Determinar o Orçamento",
                "Controlar os Custos"
            ],
            "Gerenciamento da Qualidade": [
                "Planejar o Gerenciamento da Qualidade",
                "Gerenciar a Qualidade",
                "Controlar a Qualidade"
            ],
            "Gerenciamento dos Recursos": [
                "Planejar o Gerenciamento dos Recursos",
                "Estimar os Recursos das Atividades",
                "Adquirir Recursos",
                "Desenvolver a Equipe",
                "Gerenciar a Equipe",
                "Controlar os Recursos"
            ],
            "Gerenciamento das Comunicações": [
                "Planejar o Gerenciamento das Comunicações",
                "Gerenciar as Comunicações",
                "Monitorar as Comunicações"
            ],
            "Gerenciamento dos Riscos": [
                "Planejar o Gerenciamento dos Riscos",
                "Identificar os Riscos",
                "Realizar a Análise Qualitativa dos Riscos",
                "Realizar a Análise Quantitativa dos Riscos",
                "Planejar as Respostas aos Riscos",
                "Implementar Respostas aos Riscos",
                "Monitorar os Riscos"
            ],
            "Gerenciamento das Aquisições": [
                "Planejar o Gerenciamento das Aquisições",
                "Conduzir as Aquisições",
                "Controlar as Aquisições"
            ],
            "Gerenciamento das Partes Interessadas": [
                "Identificar as Partes Interessadas",
                "Planejar o Engajamento das Partes Interessadas",
                "Gerenciar o Engajamento das Partes Interessadas",
                "Monitorar o Engajamento das Partes Interessadas"
            ]
        }
        
        # Se o tópico está no dicionário de subtópicos conhecidos
        if topic in known_subtopics:
            available_subtopics = known_subtopics[topic]
            # Se pediu mais subtópicos do que existem, retorna todos
            if num_subtopics >= len(available_subtopics):
                return available_subtopics
            # Caso contrário, retorna uma seleção aleatória
            return random.sample(available_subtopics, num_subtopics)
            
        # Se não encontrou no dicionário, gera subtópicos genéricos
        return [f"Aspecto {i+1} de {topic}" for i in range(num_subtopics)]
        
    except Exception as e:
        logger.error(f"Erro ao gerar subtópicos: {e}")
        # Em caso de erro, retorna subtópicos genéricos
        return [f"Aspecto {i+1} de {topic}" for i in range(num_subtopics)]

def generate_question_with_ai(topic: str, context: str, client: OpenAI, api_key: str, model: str = None) -> Optional[Dict]:
    """
    Gera uma única questão usando a API da OpenAI.
    
    Args:
        topic: Tópico para a questão
        context: Contexto para a questão
        client: Cliente OpenAI
        api_key: Chave da API OpenAI
        model: Modelo a ser usado (ou None para usar o padrão)
        
    Returns:
        Dict ou None: Dicionário com a questão gerada ou None em caso de erro
    """
    try:
        # Mapear ID do modelo para ID da API
        model = map_model_id_to_api(model)
        if not model:
            model = "gpt-3.5-turbo"  # Modelo padrão
            
        logger.info(f"Gerando questão com modelo: {model}")
        
        # Construir o prompt para a questão
        prompt = f"""
Crie uma questão de múltipla escolha sobre "{topic}" baseada no contexto fornecido.

Contexto:

{context}

Requisitos para a questão:
1. A questão deve ser prática e baseada em cenários realistas de gerenciamento de projetos
2. A questão deve testar compreensão profunda dos conceitos do PMBOK
3. A questão deve exigir análise e aplicação do conhecimento, não apenas memorização
4. Use linguagem clara e precisa, evitando ambiguidades
5. NÃO mencione opções de resposta (A, B, C, D) no texto da pergunta
6. A pergunta deve ser independente e não fazer referência a alternativas

Responda APENAS com um objeto JSON em português brasileiro com a seguinte estrutura:
{{
  "question": "Texto completo da questão",
  "difficulty": número de 1 a 3 representando a dificuldade (1=fácil, 2=médio, 3=difícil)
}}

Não inclua as alternativas nem a resposta correta.
"""

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um especialista em certificação PMP, responsável por criar questões de alta qualidade para treinar candidatos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1024,
            n=1,
            stop=None,
        )
        
        # Log da resposta completa para debug
        logger.debug(f"Resposta completa da API: {response}")
        
        # Extrair o conteúdo JSON da resposta
        response_text = response.choices[0].message.content.strip()
        logger.debug(f"Texto da resposta: {response_text}")
        
        try:
            # Usar a função process_openai_response para processar a resposta
            question_data = process_openai_response(response_text)
            
            # Verificar se os campos necessários existem
            if question_data and 'question' not in question_data:
                logger.error("Resposta da API não contém o campo 'question'")
                return None
                
            return question_data
            
        except KeyError as e:
            logger.error(f"Campo obrigatório ausente na resposta: {e}")
            return None
        
    except Exception as e:
        logger.error(f"Erro ao gerar questão: {e}")
        return None

def generate_answer_with_ai(question: str, context: str, client: OpenAI, api_key: str, model: str = None) -> Optional[Dict]:
    """
    Gera uma resposta e justificativa usando a API da OpenAI.
    """
    try:
        # Mapear ID do modelo para ID da API
        model = map_model_id_to_api(model)
        if not model:
            model = "gpt-3.5-turbo"  # Modelo padrão
            
        # Resto do código permanece igual
        prompt = f"""Você é um especialista em certificação PMP (Project Management Professional).
        
        Com base no contexto fornecido, gere uma resposta correta e uma justificativa detalhada para a seguinte questão:
        
        Questão:
        {question}
        
        Contexto:
        {context}
        
        A resposta e justificativa devem:
        1. Ser baseadas nos conceitos e práticas do PMBOK
        2. Usar terminologia correta e precisa
        3. Explicar por que a resposta está correta
        4. Citar referências específicas do PMBOK quando relevante
        5. Ser claras e diretas
        6. Focar nos conceitos-chave sendo testados
        7. A resposta correta deve ser CONCISA e ter no MÁXIMO 200 caracteres
        8. Evite respostas longas e complexas
        9. A resposta não pode ser que depende da situação
        10. IMPORTANTE: NUNCA faça referência a letras de opções (como "A resposta A", "Alternativa B", etc.)
        11. Forneça apenas o conteúdo da resposta, sem indicar sua posição como alternativa
        
        IMPORTANTE: Retorne APENAS um objeto JSON válido com esta estrutura exata:
        {{
            "correct_answer": "texto da resposta correta (máximo 200 caracteres)",
            "justification": "explicação detalhada de por que esta é a resposta correta, incluindo referências ao PMBOK e conceitos-chave"
        }}
        
        Não inclua nenhum texto adicional antes ou depois do JSON. O JSON deve ser válido e bem formatado."""
        
        # Fazer a chamada à API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um especialista em certificação PMP, responsável por fornecer respostas precisas e justificativas detalhadas. Sua resposta deve ser APENAS um objeto JSON válido, sem nenhum texto adicional. A resposta correta deve ser concisa (máximo 200 caracteres)."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,  # Temperatura mais baixa para respostas mais precisas
            max_tokens=800,
            response_format={ "type": "json_object" }  # Força a resposta a ser um JSON válido
        )
        
        # Log da resposta completa para debug
        logger.debug(f"Resposta da API para resposta/justificativa: {response.choices[0].message.content}")
        
        # Processar resposta
        try:
            # Usar a função process_openai_response para processar a resposta
            content = response.choices[0].message.content.strip()
            result = process_openai_response(content)
            
            # Valida os campos obrigatórios
            if not result or not isinstance(result, dict):
                raise ValueError("Resposta não é um objeto JSON válido")
                
            if 'correct_answer' not in result or not result['correct_answer']:
                raise ValueError("Campo 'correct_answer' ausente ou vazio")
                
            if 'justification' not in result or not result['justification']:
                raise ValueError("Campo 'justification' ausente ou vazio")
            
            # Truncar a resposta correta se for muito longa (reintroduzido)
            correct_answer = result['correct_answer'].strip()
            if len(correct_answer) > 200:
                logger.warning("Resposta correta gerada pela API era muito longa, truncando...")
                correct_answer = correct_answer[:197] + "..."
            
            return correct_answer, result['justification'].strip()
            
        except (KeyError, ValueError) as e:
            logger.error(f"Erro na validação da resposta: {e}")
            logger.error(f"Conteúdo recebido: {response.choices[0].message.content}")
            return None
        
    except Exception as e:
        logger.error(f"Erro ao gerar resposta: {e}")
        return None

def generate_distractors_with_ai(question: str, correct_answer: str, context: str, client: OpenAI, api_key: str, model: str = "gpt-3.5-turbo") -> tuple:
    """
    Gera distradores (alternativas incorretas) para uma questão usando IA.
    
    Args:
        question: Pergunta gerada
        correct_answer: Resposta correta
        context: Contexto relevante dos chunks de texto
        client: Cliente OpenAI
        api_key: Chave da API OpenAI
        model: Modelo a ser usado para gerar distratores
        
    Returns:
        tuple: (lista de distradores, subtópico)
    """
    try:
        messages = [
            {"role": "system", "content": """Você é um especialista em criar alternativas incorretas (distratores) para questões de certificação PMP. 
            Suas alternativas devem ser plausíveis e desafiadoras, seguindo estas diretrizes:
            
            1. Os distratores NÃO devem ser obviamente errados
            2. Cada distrator deve ser uma resposta que seria correta em um contexto diferente
            3. Os distratores devem usar conceitos do PMBOK de forma incorreta ou em contextos inadequados
            4. Evite negações simples da resposta correta
            5. Use conceitos relacionados mas que não se aplicam ao cenário específico
            6. Mantenha o mesmo nível de complexidade e formato da resposta correta
            7. Baseie os distratores no material de estudo fornecido
            8. Use terminologia correta do PMBOK, mas aplicada incorretamente
            9. Crie distratores que testem compreensão profunda, não memorização
            10. Evite opções absurdas ou claramente erradas
            11. Mantenha TODOS os distratores com tamanho máximo de 200 caracteres
            12. Se a resposta correta for curta, os distratores também devem ser curtos
            13. As alternativas devem ser concisas e diretas
            14. IMPORTANTE: NUNCA faça referência a letras de opções (como "A", "B", "C", "D") nos distratores
            15. Não inclua texto como "Alternativa A" ou similar no conteúdo dos distratores
            16. Forneça apenas o conteúdo da alternativa, sem indicar sua posição como opção
            
            Para o subtópico, escolha um aspecto específico do gerenciamento de projetos que está sendo testado, como:
            - Técnicas específicas (ex: EAP, RACI, Diagrama de Ishikawa)
            - Ferramentas (ex: Análise de Pareto, Matriz SWOT)
            - Processos específicos (ex: Definição de Escopo, Identificação de Riscos)
            - Documentos (ex: Project Charter, Plano de Gerenciamento)
            - Conceitos específicos (ex: Metas SMART, Teoria das Restrições)
            
            O subtópico deve ser mais específico que o tema principal e focar na habilidade ou conhecimento específico sendo testado.
            
            Retorne a resposta em formato JSON com esta estrutura:
            {
                "distractors": ["distrator1", "distrator2", "distrator3"],
                "subtopic": "subtópico específico"
            }"""},
            {"role": "user", "content": f"""
            Questão: {question}
            
            Resposta Correta: {correct_answer}
            
            Contexto: {context}
            
            Crie 3 alternativas incorretas (distratores) para esta questão, seguindo as diretrizes indicadas.
            O subtópico deve refletir o aspecto específico do gerenciamento de projetos que está sendo testado.
            """}
        ]
        
        # Mapear ID do modelo para ID da API
        model = map_model_id_to_api(model)
        if not model:
            model = "gpt-3.5-turbo"  # Modelo padrão
            
        # Chamada à API
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            response_format={ "type": "json_object" }
        )
        
        # Log da resposta para debug
        logger.debug(f"Resposta da API para distratores: {response.choices[0].message.content}")
        
        # Processar resposta
        try:
            # Usar a função process_openai_response para processar a resposta
            content = response.choices[0].message.content.strip()
            result = process_openai_response(content)
            
            # Valida os resultados
            if not result or 'distractors' not in result or not isinstance(result['distractors'], list):
                logger.error("Resposta da API não contém distratores válidos")
                return [], ""
                
            # Extrair distratores e subtópico
            distractors = result['distractors']
            subtopic = result.get('subtopic', "")
            
            # Validar distratores
            if len(distractors) < 1:
                logger.error("Nenhum distrator válido foi gerado")
                return [], subtopic
                
            # Limitar a 3 distratores
            distractors = distractors[:3]
            
            # Garantir que distratores estejam dentro do limite de caracteres
            truncated_distractors = []
            for d in distractors:
                if len(d) > 200:
                    truncated = d[:197] + "..."
                    truncated_distractors.append(truncated)
                else:
                    truncated_distractors.append(d)
            
            return truncated_distractors, subtopic
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"Erro ao processar resposta para distratores: {e}")
            logger.error(f"Conteúdo que falhou: {response.choices[0].message.content}")
            return [], ""
        
    except Exception as e:
        logger.error(f"Erro ao gerar distratores: {e}")
        return [], ""

def generate_wrong_answers_with_ai(question: str, correct_answer: str, context: str, client: OpenAI, api_key: str, model: str = None) -> Optional[List[str]]:
    """
    Gera uma resposta incorreta para uma questão usando a API da OpenAI.
    """
    try:
        # Mapear ID do modelo para ID da API
        model = map_model_id_to_api(model)
        if not model:
            model = "gpt-3.5-turbo"  # Modelo padrão
        
        # Prompt para gerar uma resposta incorreta
        prompt = f"""Você é um especialista em certificação PMP (Project Management Professional).
        
        Com base no contexto fornecido, gere UMA RESPOSTA INCORRETA para a seguinte questão:
        
        Questão:
        {question}
        
        Resposta Correta:
        {correct_answer}
        
        Contexto:
        {context}
        
        A resposta incorreta deve:
        1. Ser plausível mas claramente incorreta quando analisada por um especialista
        2. Usar terminologia correta do PMBOK, mas aplicada de forma inadequada
        3. Ser um "distrator de qualidade" - parecer correta à primeira vista
        4. Não ser obviamente errada ou absurda
        5. Ter um tamanho e formato similar à resposta correta
        6. Ser concisa (máximo 200 caracteres)
        7. NUNCA fazer referência a letras de opções (como "A", "B", "C", "D")
        
        IMPORTANTE: Retorne APENAS um objeto JSON válido com esta estrutura exata:
        {{
            "wrong_answer": "texto da resposta incorreta (máximo 200 caracteres)"
        }}
        
        Não inclua nenhum texto adicional antes ou depois do JSON."""
        
        # Fazer a chamada à API
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "Você é um especialista em certificação PMP, responsável por criar distratores plausíveis. Sua resposta deve ser APENAS um objeto JSON válido com a resposta incorreta, sem nenhum texto adicional."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=400,
            response_format={ "type": "json_object" }
        )
        
        # Log da resposta completa para debug
        logger.debug(f"Resposta da API para resposta incorreta: {response.choices[0].message.content}")
        
        # Processar resposta
        try:
            # Usar a função process_openai_response para processar a resposta
            content = response.choices[0].message.content.strip()
            result = process_openai_response(content)
            
            # Valida os campos obrigatórios
            if not result or not isinstance(result, dict):
                raise ValueError("Resposta não é um objeto JSON válido")
                
            if 'wrong_answer' not in result or not result['wrong_answer']:
                raise ValueError("Campo 'wrong_answer' ausente ou vazio")
            
            # Truncar a resposta incorreta se for muito longa (reintroduzido)
            wrong_answer = result['wrong_answer'].strip()
            if len(wrong_answer) > 200:
                logger.warning("Resposta incorreta gerada pela API era muito longa, truncando...")
                wrong_answer = wrong_answer[:197] + "..."
            
            return [wrong_answer]
        except (KeyError, ValueError) as e:
            logger.error(f"Erro na validação da resposta: {e}")
            logger.error(f"Conteúdo recebido: {response.choices[0].message.content}")
            return None
        
    except Exception as e:
        logger.error(f"Erro ao gerar resposta incorreta: {e}")
        return None


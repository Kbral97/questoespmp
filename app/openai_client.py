import random
import logging
import json
from typing import List, Dict, Callable, Optional
import openai
from datetime import datetime
import time
import os
from openai import OpenAI
from flask import current_app as app
from app.database.db_manager import DatabaseManager

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Pesos para cada sub-tópico dentro de cada domínio
TOPIC_WEIGHTS = {
    'People': {
        'Team Management': 0.3,
        'Leadership': 0.3,
        'Conflict Management': 0.2,
        'Communication': 0.2
    },
    'Process': {
        'Integration': 0.2,
        'Scope': 0.2,
        'Schedule': 0.2,
        'Cost': 0.2,
        'Quality': 0.1,
        'Resource': 0.1
    },
    'Business Environment': {
        'Strategic Alignment': 0.4,
        'Compliance': 0.3,
        'Value Delivery': 0.3
    }
}

# Mapeamento de tópicos para sub-tópicos
TOPIC_SUBTOPICS = {
    'people': [
        'team_management',
        'leadership',
        'conflict_management',
        'stakeholder_management',
        'communication_management'
    ],
    'process': [
        'integration_management',
        'scope_management',
        'schedule_management',
        'cost_management',
        'quality_management',
        'resource_management',
        'risk_management',
        'procurement_management'
    ],
    'business_environment': [
        'strategic_alignment',
        'business_value',
        'organizational_change',
        'compliance',
        'market_analysis'
    ]
}

def select_subtopic(topic: str) -> str:
    """
    Seleciona aleatoriamente um sub-tópico baseado no tópico principal.
    
    Args:
        topic: Tópico principal (people, process, business_environment)
        
    Returns:
        Sub-tópico selecionado aleatoriamente
        
    Raises:
        ValueError: Se o tópico não for válido
    """
    if topic not in TOPIC_SUBTOPICS:
        raise ValueError(f"Tópico inválido: {topic}. Deve ser um dos seguintes: {list(TOPIC_SUBTOPICS.keys())}")
    
    return random.choice(TOPIC_SUBTOPICS[topic])

def generate_questions_with_specialized_models(
    topic: str,
    num_questions: int,
    num_subtopics: int = 1,
    api_key: Optional[str] = None,
    callback: Optional[Callable[[int, int], None]] = None
) -> List[Dict[str, str]]:
    """
    Gera múltiplas questões usando modelos especializados por tópico.
    
    Args:
        topic: Tópico principal das questões (people, process, business_environment)
        num_questions: Número de questões a serem geradas
        num_subtopics: Número de sub-tópicos a serem incluídos (padrão: 1)
        api_key: Chave da API OpenAI (opcional)
        callback: Função de callback para atualizar o progresso (opcional)
        
    Returns:
        Lista de dicionários contendo as questões geradas
    """
    questions = []
    retries = 3  # Número máximo de tentativas por questão
    
    # Define os sub-tópicos baseado no tópico principal
    subtopics = {
        'people': [
            'team_management',
            'conflict_management',
            'stakeholder_management',
            'communication_management'
        ],
        'process': [
            'integration_management',
            'scope_management',
            'schedule_management',
            'cost_management',
            'quality_management'
        ],
        'business_environment': [
            'business_analysis',
            'strategic_alignment',
            'benefits_management',
            'organizational_change'
        ]
    }
    
    if topic not in subtopics:
        raise ValueError(f"Tópico inválido: {topic}. Use: {', '.join(subtopics.keys())}")
    
    # Seleciona aleatoriamente o número especificado de sub-tópicos
    selected_subtopics = random.sample(subtopics[topic], min(num_subtopics, len(subtopics[topic])))
    
    # Distribui as questões entre os sub-tópicos selecionados
    questions_per_subtopic = num_questions // len(selected_subtopics)
    remaining_questions = num_questions % len(selected_subtopics)
    
    for subtopic in selected_subtopics:
        # Calcula quantas questões gerar para este sub-tópico
        num_questions_for_subtopic = questions_per_subtopic
        if remaining_questions > 0:
            num_questions_for_subtopic += 1
            remaining_questions -= 1
        
        for i in range(num_questions_for_subtopic):
            # Tenta gerar a questão com retry em caso de falha
            for attempt in range(retries):
                try:
                    question = generate_question(
                        topic=topic,
                        subtopic=subtopic,
                        api_key=api_key
                    )
                    
                    if question:
                        questions.append(question)
                        current_progress = len(questions)
                        logging.info(f"Questão {current_progress}/{num_questions} gerada com sucesso")
                        
                        # Chama o callback se fornecido
                        if callback:
                            callback(current_progress, num_questions)
                        break
                        
                except Exception as e:
                    logging.warning(f"Tentativa {attempt + 1} falhou para questão {len(questions) + 1}: {str(e)}")
                    if attempt == retries - 1:
                        logging.error(f"Falha ao gerar questão após {retries} tentativas")
                    time.sleep(1)  # Espera 1 segundo antes de tentar novamente
    
    return questions

def generate_question(topic: str, subtopic: str, api_key: Optional[str] = None) -> Dict:
    """
    Gera uma única questão usando a API da OpenAI.
    
    Args:
        topic: Tópico principal (people, process, business_environment)
        subtopic: Sub-tópico específico
        api_key: Chave da API da OpenAI (opcional)
        
    Returns:
        Dicionário contendo a questão gerada com suas informações
        
    Raises:
        ValueError: Se os parâmetros forem inválidos
        Exception: Se houver erro na geração da questão
    """
    if not api_key:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError("Chave da API da OpenAI não encontrada")
    
    if topic not in TOPIC_SUBTOPICS:
        raise ValueError(f"Tópico inválido: {topic}")
    
    if subtopic not in TOPIC_SUBTOPICS[topic]:
        raise ValueError(f"Sub-tópico {subtopic} não pertence ao tópico {topic}")
    
    try:
        client = OpenAI(api_key=api_key)
        
        # Prompt para geração da questão
        prompt = f"""
        Gere uma questão de múltipla escolha para o exame PMP sobre o tópico {topic} e sub-tópico {subtopic}.
        
        A questão deve:
        1. Ser clara e concisa
        2. Ter 4 opções de resposta
        3. Ter apenas uma resposta correta
        4. Incluir uma explicação detalhada da resposta correta
        5. Seguir o formato PMP de questões
        6. Ter um nível de dificuldade compatível com o exame PMP real
        
        Retorne a resposta no formato JSON com os seguintes campos:
        - question: texto da questão
        - options: lista com as 4 opções
        - correct_answer: índice da opção correta (0-3)
        - explanation: explicação detalhada da resposta correta
        """
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um especialista em gerenciamento de projetos e certificação PMP."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        
        # Processa a resposta
        content = response.choices[0].message.content
        try:
            question_data = json.loads(content)
        except json.JSONDecodeError:
            logger.error(f"Erro ao decodificar resposta da API: {content}")
            raise ValueError("Resposta da API em formato inválido")
        
        # Adiciona metadados
        question_data.update({
            'topic': topic,
            'subtopic': subtopic,
            'created_at': datetime.now().isoformat()
        })
        
        return question_data
        
    except Exception as e:
        logger.error(f"Erro ao gerar questão: {str(e)}")
        raise

def generate_questions(topic, num_questions=5, num_subtopics=3, api_key=None):
    """
    Generate questions about a topic using OpenAI's API.
    """
    logger.info("=== Iniciando geração de questões via OpenAI ===")
    logger.info(f"Parâmetros recebidos: topic={topic}, num_questions={num_questions}, num_subtopics={num_subtopics}")
    
    try:
        # Validate input
        if not isinstance(topic, str) or not topic.strip():
            logger.error(f"Tópico inválido: {topic}")
            raise ValueError("Topic must be a non-empty string")
        if not isinstance(num_questions, int) or num_questions < 1:
            logger.error(f"Número de questões inválido: {num_questions}")
            raise ValueError("num_questions must be a positive integer")
        if not isinstance(num_subtopics, int) or num_subtopics < 1:
            logger.error(f"Número de sub-tópicos inválido: {num_subtopics}")
            raise ValueError("num_subtopics must be a positive integer")
            
        # Use environment API key if none provided
        if not api_key:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                logger.error("Chave da API OpenAI não encontrada")
                raise ValueError("OpenAI API key not found")
            logger.info("Usando chave da API do ambiente")
        
        logger.info("Inicializando cliente OpenAI")
        try:
            client = OpenAI(api_key=api_key)
            # Test the API key with a simple completion
            test_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            logger.info("Teste de conexão com OpenAI bem sucedido")
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente OpenAI: {str(e)}")
            raise ValueError(f"Failed to initialize OpenAI client: {str(e)}")
        
        # Initialize DatabaseManager
        try:
            db_manager = DatabaseManager()
            logger.info("DatabaseManager inicializado com sucesso")
        except Exception as e:
            logger.error(f"Erro ao inicializar DatabaseManager: {str(e)}")
            raise ValueError(f"Failed to initialize DatabaseManager: {str(e)}")
        
        # Generate subtopics first
        logger.info("Gerando sub-tópicos...")
        try:
            subtopics_response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{
                    "role": "system",
                    "content": "You are a PMP certification expert. Generate specific subtopics for the given topic."
                }, {
                    "role": "user",
                    "content": f"Generate {num_subtopics} specific subtopics for the PMP topic: {topic}. Return only the subtopics as a comma-separated list."
                }],
                temperature=0.7
            )
            
            if not subtopics_response.choices or not subtopics_response.choices[0].message.content:
                raise ValueError("No subtopics generated")
                
            subtopics = subtopics_response.choices[0].message.content.split(',')
            subtopics = [s.strip() for s in subtopics[:num_subtopics]]
            logger.info(f"Sub-tópicos gerados: {subtopics}")
        except Exception as e:
            logger.error(f"Erro ao gerar sub-tópicos: {str(e)}")
            raise ValueError(f"Failed to generate subtopics: {str(e)}")
        
        # Calculate questions per subtopic
        questions_per_subtopic = num_questions // len(subtopics)
        extra_questions = num_questions % len(subtopics)
        logger.info(f"Distribuição de questões: {questions_per_subtopic} por sub-tópico + {extra_questions} extra")
        
        questions = []
        for i, subtopic in enumerate(subtopics):
            current_questions = questions_per_subtopic + (1 if i < extra_questions else 0)
            logger.info(f"Gerando {current_questions} questões para o sub-tópico: {subtopic}")
            
            if current_questions > 0:
                try:
                    response = client.chat.completions.create(
                        model="gpt-3.5-turbo",
                        messages=[{
                            "role": "system",
                            "content": """You are a PMP certification expert. Generate multiple-choice questions in JSON format.
                            Each question must be a JSON object with the following structure:
                            {
                                "question": "Question text",
                                "options": ["Option A", "Option B", "Option C", "Option D"],
                                "correct_answer": "A",
                                "explanation": "Detailed explanation"
                            }
                            Return all questions as a JSON array."""
                        }, {
                            "role": "user",
                            "content": f"""Generate {current_questions} multiple-choice PMP questions about {subtopic} (related to {topic}).
                            Format each question as a JSON object with the following structure:
                            {{
                                "question": "Question text",
                                "options": ["Option A", "Option B", "Option C", "Option D"],
                                "correct_answer": "A",
                                "explanation": "Detailed explanation"
                            }}
                            Return all questions as a JSON array."""
                        }],
                        temperature=0.7
                    )
                    
                    content = response.choices[0].message.content
                    logger.info(f"Resposta recebida para sub-tópico {subtopic}")
                    logger.debug(f"Conteúdo da resposta: {content}")
                    
                    try:
                        # Try to clean the response if it's not valid JSON
                        content = content.strip()
                        if not content.startswith('['):
                            content = '[' + content
                        if not content.endswith(']'):
                            content = content + ']'
                            
                        subtopic_questions = json.loads(content)
                        if not isinstance(subtopic_questions, list):
                            logger.error(f"Resposta não é uma lista: {type(subtopic_questions)}")
                            continue
                            
                        logger.info(f"Adicionando {len(subtopic_questions)} questões do sub-tópico {subtopic}")
                        
                        # Validate and save each question
                        for q in subtopic_questions:
                            try:
                                # Validate question format
                                required_fields = ['question', 'options', 'correct_answer', 'explanation']
                                if not all(field in q for field in required_fields):
                                    logger.error(f"Questão faltando campos obrigatórios: {q}")
                                    continue
                                
                                if not isinstance(q['options'], list) or len(q['options']) != 4:
                                    logger.error(f"Formato inválido das opções: {q['options']}")
                                    continue
                                
                                # Add metadata
                                q['topic'] = topic
                                q['subtopic'] = subtopic
                                
                                questions.append(q)
                            except Exception as e:
                                logger.error(f"Erro ao processar questão: {str(e)}")
                                continue
                                
                    except json.JSONDecodeError as e:
                        logger.error(f"Erro ao decodificar JSON para sub-tópico {subtopic}: {str(e)}")
                        logger.error(f"Conteúdo que causou o erro: {content}")
                        continue
                except Exception as e:
                    logger.error(f"Erro ao gerar questões para sub-tópico {subtopic}: {str(e)}")
                    logger.exception("Stacktrace completo:")
                    continue
        
        # Only try to save questions if we have any
        if questions:
            logger.info(f"Salvando {len(questions)} questões no banco de dados")
            for q in questions:
                try:
                    db_manager.add_question({
                        'question': q['question'],
                        'options': q['options'],
                        'correct_answer': q['correct_answer'],
                        'explanation': q.get('explanation', ''),
                        'topic': q['topic'],
                        'subtopic': q['subtopic'],
                        'difficulty': q.get('difficulty', 1)
                    })
                except Exception as e:
                    logger.error(f"Erro ao salvar questão no banco de dados: {str(e)}")
                    continue
        else:
            logger.error("Nenhuma questão foi gerada com sucesso")
            raise ValueError("No questions were generated successfully")
        
        logger.info(f"Geração concluída. Total de questões geradas: {len(questions)}")
        return questions
        
    except Exception as e:
        logger.error(f"Erro na função generate_questions: {str(e)}")
        logger.exception("Stacktrace completo:")
        raise 
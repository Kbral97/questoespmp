import random
import logging
import json
from typing import List, Dict, Callable, Optional
import openai
from datetime import datetime
import time
import os
from openai import OpenAI

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

def generate_questions(topic: str, num_questions: int = 5, api_key: Optional[str] = None) -> List[Dict]:
    """
    Gera múltiplas questões para um tópico específico.
    
    Args:
        topic: Tópico principal (people, process, business_environment)
        num_questions: Número de questões a serem geradas (padrão: 5)
        api_key: Chave da API da OpenAI (opcional)
        
    Returns:
        Lista de dicionários contendo as questões geradas
        
    Raises:
        ValueError: Se os parâmetros forem inválidos
        Exception: Se houver erro na geração das questões
    """
    if not isinstance(num_questions, int) or num_questions < 1:
        raise ValueError("Número de questões deve ser um inteiro positivo")
    
    questions = []
    difficulties = ['easy', 'medium', 'hard']
    
    try:
        for i in range(num_questions):
            # Seleciona um sub-tópico aleatório
            subtopic = select_subtopic(topic)
            
            # Distribui as dificuldades de forma equilibrada
            difficulty = difficulties[i % len(difficulties)]
            
            # Gera a questão
            question = generate_question(
                topic=topic,
                subtopic=subtopic,
                difficulty=difficulty,
                api_key=api_key
            )
            
            questions.append(question)
            
            # Adiciona um pequeno delay entre as requisições para evitar rate limiting
            if i < num_questions - 1:
                time.sleep(1)
        
        return questions
        
    except Exception as e:
        logger.error(f"Erro ao gerar questões: {str(e)}")
        raise 
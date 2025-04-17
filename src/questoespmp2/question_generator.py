import os
import json
import logging
from typing import Dict, List, Any, Optional
from .api.openai_client import (
    generate_questions_with_specialized_models,
    get_openai_client
)
from .database.db_manager import DatabaseManager
from .config import Config

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuestionGenerator:
    def __init__(self, config: Config):
        """
        Inicializa o gerador de questões.
        
        Args:
            config: Objeto de configuração
        """
        self.config = config
        self.db = DatabaseManager()
        self.api_key = os.getenv("OPENAI_API_KEY")
        
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY não encontrada nas variáveis de ambiente")
    
    def generate_questions(self, topic: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Gera questões sobre um tópico específico.
        
        Args:
            topic: Tópico para gerar questões
            num_questions: Número de questões a gerar
            
        Returns:
            Lista de questões geradas
        """
        try:
            logger.info(f"Gerando {num_questions} questões sobre {topic}")
            
            # Verificar se o tópico existe no banco de dados
            if not self.db.topic_exists(topic):
                logger.error(f"Tópico {topic} não encontrado no banco de dados")
                return []
            
            # Obter informações dos modelos
            models_info = {
                'question_model': self.config.get_model('question_model'),
                'answer_model': self.config.get_model('answer_model'),
                'wrong_answers_model': self.config.get_model('wrong_answers_model')
            }
            
            # Gerar questões usando os modelos especializados
            questions = generate_questions_with_specialized_models(
                topic=topic,
                num_questions=num_questions,
                api_key=self.api_key
            )
            
            # Salvar questões no banco de dados
            for question in questions:
                self.db.save_question(question)
            
            logger.info(f"Geradas e salvas {len(questions)} questões")
            return questions
            
        except Exception as e:
            logger.error(f"Erro ao gerar questões: {str(e)}")
            return []
    
    def get_questions_by_topic(self, topic: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Obtém questões existentes sobre um tópico.
        
        Args:
            topic: Tópico para buscar questões
            num_questions: Número de questões a retornar
            
        Returns:
            Lista de questões
        """
        try:
            return self.db.get_questions_by_topic(topic, num_questions)
        except Exception as e:
            logger.error(f"Erro ao buscar questões: {str(e)}")
            return []
    
    def get_question_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """
        Obtém uma questão específica pelo ID.
        
        Args:
            question_id: ID da questão
            
        Returns:
            Questão encontrada ou None
        """
        try:
            return self.db.get_question_by_id(question_id)
        except Exception as e:
            logger.error(f"Erro ao buscar questão: {str(e)}")
            return None
    
    def delete_question(self, question_id: str) -> bool:
        """
        Remove uma questão do banco de dados.
        
        Args:
            question_id: ID da questão
            
        Returns:
            True se removida com sucesso, False caso contrário
        """
        try:
            return self.db.delete_question(question_id)
        except Exception as e:
            logger.error(f"Erro ao remover questão: {str(e)}")
            return False 
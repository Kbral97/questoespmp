#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database manager for PMP Questions Generator
"""

import os
import sqlite3
import platform
import json
import logging
import math
from typing import Union, Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

def get_db_path():
    """Get the path to the database file."""
    if platform.system() == 'Windows':
        local_app_data = os.getenv('LOCALAPPDATA')
        db_dir = os.path.join(local_app_data, 'Packages', 'PythonSoftwareFoundation.Python.3.11_qbz5n2kfra8p0', 'LocalCache', 'Local', 'QuestoesGenerator', 'db')
    else:
        home = os.path.expanduser('~')
        db_dir = os.path.join(home, '.questoespmp', 'db')
    
    # Create directory if it doesn't exist
    os.makedirs(db_dir, exist_ok=True)
    
    return os.path.join(db_dir, 'questions.db')

class DatabaseManager:
    """Manages database operations for the PMP Questions Generator."""
    
    _instance = None
    
    def __new__(cls):
        """Implement Singleton pattern."""
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize database manager and create necessary tables."""
        if self._initialized:
            return
            
        self._initialized = True
        self.questions_db = get_db_path()
        self.data_dir = os.path.dirname(self.questions_db)
        
        # Initialize all databases in the same directory
        self.config_db = os.path.join(self.data_dir, 'config.db')
        self.sessions_db = os.path.join(self.data_dir, 'sessions.db')
        self.stats_db = os.path.join(self.data_dir, 'user_statistics.db')
        self.models_db = os.path.join(self.data_dir, 'fine_tuned_models.db')
        self.jobs_db = os.path.join(self.data_dir, 'training_jobs.db')
        
        # Create database directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Setup databases and tables
        self.setup_databases()
    
    def setup_databases(self):
        """Create all necessary databases and tables."""
        # Questions database
        with sqlite3.connect(self.questions_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    options TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    explanation TEXT,
                    topic TEXT,
                    subtopic TEXT,
                    difficulty INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Add text_chunks table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS text_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    raw_text TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    chunk_number INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    embedding TEXT,  -- Store embeddings as JSON string
                    UNIQUE(file_name, chunk_number)
                )
            ''')
            
            # Add question_feedback table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS question_feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_text TEXT NOT NULL,
                    options TEXT,
                    correct_answer TEXT,
                    explanation TEXT,
                    feedback_type TEXT NOT NULL,
                    feedback_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        # Config database
        with sqlite3.connect(self.config_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
        
        # Sessions database
        with sqlite3.connect(self.sessions_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    end_time TIMESTAMP,
                    questions_answered INTEGER DEFAULT 0,
                    correct_answers INTEGER DEFAULT 0,
                    topics TEXT
                )
            ''')
        
        # User statistics database
        with sqlite3.connect(self.stats_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS user_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    questions_answered INTEGER DEFAULT 0,
                    correct_answers INTEGER DEFAULT 0,
                    last_session TIMESTAMP,
                    UNIQUE(topic)
                )
            ''')
        
        # Fine-tuned models database
        with sqlite3.connect(self.models_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS fine_tuned_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_name TEXT NOT NULL,
                    custom_name TEXT,
                    base_model TEXT NOT NULL,
                    training_data TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(model_name)
                )
            ''')
        
        # Training jobs database
        with sqlite3.connect(self.jobs_db) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS training_jobs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id INTEGER,
                    status TEXT NOT NULL,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_message TEXT,
                    FOREIGN KEY(model_id) REFERENCES fine_tuned_models(id)
                )
            ''')
    
    def get_db_connection(self, db_type: str) -> sqlite3.Connection:
        """Get a connection to the specified database."""
        db_map = {
            'questions': self.questions_db,
            'config': self.config_db,
            'sessions': self.sessions_db,
            'stats': self.stats_db,
            'models': self.models_db,
            'jobs': self.jobs_db
        }
        
        if db_type not in db_map:
            raise ValueError(f"Unknown database type: {db_type}")
            
        db_path = db_map[db_type]
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        return sqlite3.connect(db_path)

    def save_question(self, question_data: Dict[str, Any]) -> int:
        """Save a question to the database."""
        with self.get_db_connection('questions') as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO questions (question, options, correct_answer, explanation, topic, subtopic, difficulty)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                question_data['question'],
                json.dumps(question_data['options']),  # Use json instead of str
                question_data['correct_answer'],
                question_data.get('explanation', ''),
                question_data.get('topic', ''),
                question_data.get('subtopic', ''),
                question_data.get('difficulty', 1)
            ))
            return cursor.lastrowid

    def get_random_question(self) -> Optional[Dict[str, Any]]:
        """Get a random question from the database."""
        with self.get_db_connection('questions') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT 1')
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return {
                'id': row[0],
                'question': row[1],
                'options': json.loads(row[2]),  # Use json instead of eval
                'correct_answer': row[3],
                'explanation': row[4],
                'topic': row[5],
                'subtopic': row[6],
                'difficulty': row[7]
            }

    def insert_question(self, question_data: Dict[str, Any]) -> int:
        """
        Insert a question into the database.
        This is an alias for save_question for backward compatibility.
        
        Args:
            question_data: Dictionary containing question data
            
        Returns:
            int: ID of the inserted question
        """
        return self.save_question(question_data)

    def question_exists(self, question_text: str) -> bool:
        """Check if a question already exists in the database."""
        with self.get_db_connection('questions') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM questions WHERE question = ?', (question_text,))
            count = cursor.fetchone()[0]
            return count > 0

    def get_statistics(self) -> Dict[str, Any]:
        """Get user statistics."""
        try:
            with self.get_db_connection('stats') as conn:
                cursor = conn.cursor()
                
                # Get overall statistics
                cursor.execute('''
                    SELECT 
                        COALESCE(SUM(questions_answered), 0) as total_questions,
                        COALESCE(SUM(correct_answers), 0) as total_correct
                    FROM user_statistics
                ''')
                total_questions, total_correct = cursor.fetchone()
                
                # Calculate overall accuracy
                accuracy = (total_correct / total_questions) if total_questions > 0 else 0
                
                # Get best topic (minimum 5 questions answered)
                cursor.execute('''
                    SELECT 
                        topic,
                        ROUND(CAST(correct_answers AS FLOAT) * 100.0 / questions_answered, 1) as accuracy,
                        questions_answered
                    FROM user_statistics
                    WHERE questions_answered >= 5
                    ORDER BY 
                        CAST(correct_answers AS FLOAT) / questions_answered DESC,
                        questions_answered DESC
                    LIMIT 1
                ''')
                best_topic_row = cursor.fetchone()
                
                # Get worst topic (minimum 5 questions answered)
                cursor.execute('''
                    SELECT 
                        topic,
                        ROUND(CAST(correct_answers AS FLOAT) * 100.0 / questions_answered, 1) as accuracy,
                        questions_answered
                    FROM user_statistics
                    WHERE questions_answered >= 5
                    ORDER BY 
                        CAST(correct_answers AS FLOAT) / questions_answered ASC,
                        questions_answered DESC
                    LIMIT 1
                ''')
                worst_topic_row = cursor.fetchone()
                
                return {
                    'total_questions': total_questions,
                    'total_correct': total_correct,
                    'accuracy': accuracy,
                    'best_topic': {
                        'topic': best_topic_row[0] if best_topic_row else None,
                        'accuracy': best_topic_row[1] if best_topic_row else 0,
                        'questions': best_topic_row[2] if best_topic_row else 0
                    } if best_topic_row else None,
                    'worst_topic': {
                        'topic': worst_topic_row[0] if worst_topic_row else None,
                        'accuracy': worst_topic_row[1] if worst_topic_row else 0,
                        'questions': worst_topic_row[2] if worst_topic_row else 0
                    } if worst_topic_row else None
                }
        except Exception as e:
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {
                'total_questions': 0,
                'total_correct': 0,
                'accuracy': 0,
                'best_topic': None,
                'worst_topic': None
            }

    def update_question_stats(self, question_id: int, correct: bool):
        """Update statistics after answering a question."""
        try:
            # Get question topic
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT topic FROM questions WHERE id = ?', (question_id,))
                row = cursor.fetchone()
                
                if not row:
                    logger.error(f"Questão não encontrada: {question_id}")
                    return
                    
                topic = row[0] or 'Geral'  # Use 'Geral' if topic is None
            
            # Update statistics
            with self.get_db_connection('stats') as conn:
                cursor = conn.cursor()
                
                # Try to update existing record
                cursor.execute('''
                    INSERT INTO user_statistics (
                        topic, 
                        questions_answered, 
                        correct_answers, 
                        last_session
                    )
                    VALUES (?, 1, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(topic) DO UPDATE SET
                        questions_answered = questions_answered + 1,
                        correct_answers = correct_answers + ?,
                        last_session = CURRENT_TIMESTAMP
                ''', (topic, 1 if correct else 0, 1 if correct else 0))
                
                conn.commit()
                logger.info(f"Estatísticas atualizadas para o tópico: {topic}")
                
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas: {e}")

    def find_most_relevant_chunks(self, query: str, num_chunks: int = 5) -> List[Dict[str, Any]]:
        """
        Find the most relevant chunks of text from the database based on a query using TF-IDF.
        
        Args:
            query: Search query
            num_chunks: Number of chunks to return
            
        Returns:
            List of most relevant chunks with their scores
        """
        try:
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                
                # Get all text chunks
                cursor.execute('SELECT id, raw_text, file_name FROM text_chunks')
                rows = cursor.fetchall()
                
                if not rows:
                    logger.warning("No text chunks found in database")
                    return []
                
                # Prepare texts for vectorization
                texts = [row[1] for row in rows]  # raw_text
                texts.insert(0, query)  # Add query as first text
                
                # Create TF-IDF vectorizer
                from sklearn.feature_extraction.text import TfidfVectorizer
                vectorizer = TfidfVectorizer(
                    stop_words='english',
                    ngram_range=(1, 2),
                    max_features=5000
                )
                
                # Vectorize texts
                try:
                    tfidf_matrix = vectorizer.fit_transform(texts)
                except Exception as e:
                    logger.error(f"Error vectorizing texts: {e}")
                    return []
                
                # Calculate cosine similarity
                from sklearn.metrics.pairwise import cosine_similarity
                try:
                    # Get query vector (first text)
                    query_vector = tfidf_matrix[0:1]
                    # Calculate similarity with all chunks
                    similarities = cosine_similarity(query_vector, tfidf_matrix[1:]).flatten()
                except Exception as e:
                    logger.error(f"Error calculating similarities: {e}")
                    return []
                
                # Sort chunks by similarity
                chunk_scores = list(zip(rows, similarities))
                chunk_scores.sort(key=lambda x: x[1], reverse=True)
                
                # Return most relevant chunks
                relevant_chunks = []
                for (chunk_id, raw_text, file_name), score in chunk_scores[:num_chunks]:
                    chunk = {
                        'id': chunk_id,
                        'raw_text': raw_text,
                        'file_name': file_name,
                        'relevance_score': float(score)
                    }
                    relevant_chunks.append(chunk)
                
                logger.info(f"Found {len(relevant_chunks)} relevant chunks for query '{query}'")
                return relevant_chunks
                
        except sqlite3.Error as e:
            logger.error(f"Database error in find_most_relevant_chunks: {e}")
            return []
        except Exception as e:
            logger.error(f"Error finding relevant chunks: {e}")
            return []

    def get_question_by_text(self, question_text: str) -> Union[dict, None]:
        """Retrieve a question from the database by its text."""
        try:
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                
                # Query the database for the question
                cursor.execute('''
                    SELECT 
                        question, options, correct_answer, topic, subtopic, explanation
                    FROM questions
                    WHERE question = ?
                ''', (question_text,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                    
                # Convert row to dictionary
                options = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                return {
                    'question': row[0],
                    'options': options,
                    'correct_answer': row[2],
                    'topic': row[3],
                    'subtopic': row[4],
                    'explanation': row[5]
                }
                
        except sqlite3.Error as e:
            logger.error(f"Database error in get_question_by_text: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting question: {e}")
            return None

    def clear_all_questions(self):
        """Delete all questions from the database."""
        try:
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM questions')
                conn.commit()
                
            # Também limpar as estatísticas
            with self.get_db_connection('stats') as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM user_statistics')
                conn.commit()
                
            logger.info("Todas as questões e estatísticas foram removidas do banco de dados")
            return True
        except Exception as e:
            logger.error(f"Erro ao limpar o banco de dados: {e}")
            return False

    def get_available_subtopics(self, topic: str) -> List[str]:
        """
        Obtém a lista de subtópicos disponíveis para um tópico específico.
        
        Args:
            topic: Tópico principal
            
        Returns:
            Lista de subtópicos disponíveis
        """
        try:
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT DISTINCT subtopic 
                    FROM questions 
                    WHERE topic = ? AND subtopic IS NOT NULL AND subtopic != ''
                ''', (topic,))
                
                subtopics = [row[0] for row in cursor.fetchall()]
                
                # Se não houver subtópicos, retornar lista vazia
                if not subtopics:
                    logger.info(f"Nenhum subtópico encontrado para o tópico: {topic}")
                    return []
                
                return subtopics
                
        except Exception as e:
            logger.error(f"Erro ao obter subtópicos disponíveis: {e}")
            return []

    def topic_exists(self, topic: str) -> bool:
        """
        Verifica se um tópico existe no banco de dados.
        
        Args:
            topic: Tópico a verificar
            
        Returns:
            True se o tópico existe, False caso contrário
        """
        try:
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM questions WHERE topic = ?', (topic,))
                count = cursor.fetchone()[0]
                return count > 0
        except Exception as e:
            logger.error(f"Erro ao verificar existência do tópico: {e}")
            return False
    
    def get_questions_by_topic(self, topic: str, num_questions: int = 5) -> List[Dict[str, Any]]:
        """
        Obtém questões sobre um tópico específico.
        
        Args:
            topic: Tópico para buscar questões
            num_questions: Número de questões a retornar
            
        Returns:
            Lista de questões
        """
        try:
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, question, options, correct_answer, explanation, topic, subtopic, difficulty
                    FROM questions
                    WHERE topic = ?
                    ORDER BY RANDOM()
                    LIMIT ?
                ''', (topic, num_questions))
                
                questions = []
                for row in cursor.fetchall():
                    questions.append({
                        'id': row[0],
                        'question': row[1],
                        'options': json.loads(row[2]) if isinstance(row[2], str) else row[2],
                        'correct_answer': row[3],
                        'explanation': row[4],
                        'topic': row[5],
                        'subtopic': row[6],
                        'difficulty': row[7]
                    })
                
                return questions
        except Exception as e:
            logger.error(f"Erro ao buscar questões por tópico: {e}")
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
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, question, options, correct_answer, explanation, topic, subtopic, difficulty
                    FROM questions
                    WHERE id = ?
                ''', (question_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    'id': row[0],
                    'question': row[1],
                    'options': json.loads(row[2]) if isinstance(row[2], str) else row[2],
                    'correct_answer': row[3],
                    'explanation': row[4],
                    'topic': row[5],
                    'subtopic': row[6],
                    'difficulty': row[7]
                }
        except Exception as e:
            logger.error(f"Erro ao buscar questão por ID: {e}")
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
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Erro ao remover questão: {e}")
            return False

    def insert_text_chunk(self, chunk_data: Dict[str, Any]) -> bool:
        """
        Insert a text chunk into the database.
        
        Args:
            chunk_data: Dictionary containing:
                - raw_text: The text content of the chunk
                - file_name: Name of the source file
                - chunk_number: Sequential number of the chunk in the file
                - embedding: Optional embedding vector as JSON string
                
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                
                # Check required fields
                required_fields = ['raw_text', 'file_name', 'chunk_number']
                if not all(field in chunk_data for field in required_fields):
                    logger.error("Missing required fields in chunk data")
                    return False
                
                # Insert chunk
                cursor.execute('''
                    INSERT OR REPLACE INTO text_chunks 
                    (raw_text, file_name, chunk_number, embedding, created_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    chunk_data['raw_text'],
                    chunk_data['file_name'],
                    chunk_data['chunk_number'],
                    chunk_data.get('embedding')  # Optional field
                ))
                
                conn.commit()
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Error inserting text chunk: {e}")
            return False

    def remove_chunks_by_file(self, file_name: str) -> bool:
        """
        Remove all chunks associated with a specific file.
        
        Args:
            file_name: Name of the file whose chunks should be removed
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM text_chunks WHERE file_name = ?', (file_name,))
                conn.commit()
                
                logger.info(f"Removed all chunks for file: {file_name}")
                return True
                
        except sqlite3.Error as e:
            logger.error(f"Database error in remove_chunks_by_file: {e}")
            return False
        except Exception as e:
            logger.error(f"Error removing chunks: {e}")
            return False

    def set_model_custom_name(self, model_name: str, custom_name: str) -> bool:
        """
        Define um nome personalizado para um modelo.
        
        Args:
            model_name: Nome original do modelo
            custom_name: Nome personalizado
            
        Returns:
            bool: True se bem sucedido, False caso contrário
        """
        try:
            with self.get_db_connection('models') as conn:
                cursor = conn.cursor()
                
                # Verificar se o modelo já existe na tabela
                cursor.execute('''
                    SELECT COUNT(*) FROM fine_tuned_models WHERE model_name = ?
                ''', (model_name,))
                
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    # Atualizar o registro existente
                    cursor.execute('''
                        UPDATE fine_tuned_models 
                        SET custom_name = ? 
                        WHERE model_name = ?
                    ''', (custom_name, model_name))
                else:
                    # Inserir um novo registro
                    cursor.execute('''
                        INSERT INTO fine_tuned_models 
                        (model_name, custom_name, base_model, status) 
                        VALUES (?, ?, ?, ?)
                    ''', (model_name, custom_name, "unknown", "imported"))
                
                conn.commit()
                logger.info(f"Nome personalizado '{custom_name}' definido para o modelo '{model_name}'")
                return True
        except sqlite3.Error as e:
            logger.error(f"Erro ao definir nome personalizado: {e}")
            return False

    def get_model_custom_name(self, model_name: str) -> Optional[str]:
        """
        Obtém o nome personalizado de um modelo.
        
        Args:
            model_name: Nome original do modelo
            
        Returns:
            str: Nome personalizado ou None se não existir
        """
        try:
            with self.get_db_connection('models') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT custom_name 
                    FROM fine_tuned_models 
                    WHERE model_name = ?
                ''', (model_name,))
                row = cursor.fetchone()
                return row[0] if row else None
        except sqlite3.Error as e:
            logger.error(f"Erro ao obter nome personalizado: {e}")
            return None

    def reset_fine_tuned_models(self):
        """Reseta a tabela de modelos fine-tuned, removendo todos os registros."""
        try:
            with self.get_db_connection('models') as conn:
                conn.execute('DELETE FROM fine_tuned_models')
                conn.execute('DELETE FROM training_jobs')
                conn.commit()
            logger.info("Tabela de modelos fine-tuned resetada com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao resetar tabela de modelos: {e}")
            return False 
            
    def get_total_questions_in_database(self) -> int:
        """
        Retorna o número total de questões armazenadas no banco de dados.
        
        Returns:
            int: Total de questões
        """
        try:
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM questions')
                total = cursor.fetchone()[0]
                return total
        except Exception as e:
            logger.error(f"Erro ao obter total de questões: {e}")
            return 0
            
    def get_all_topics(self) -> List[Dict[str, Any]]:
        """
        Retorna todos os tópicos com estatísticas.
        
        Returns:
            List[Dict]: Lista de dicionários com informações de cada tópico
        """
        try:
            with self.get_db_connection('stats') as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT 
                        topic,
                        questions_answered,
                        correct_answers,
                        CASE 
                            WHEN questions_answered > 0 THEN 
                                ROUND(CAST(correct_answers AS FLOAT) * 100.0 / questions_answered, 1)
                            ELSE 0 
                        END as accuracy
                    FROM user_statistics
                    ORDER BY topic
                ''')
                
                topics = []
                for row in cursor.fetchall():
                    topics.append({
                        'topic': row[0],
                        'questions_answered': row[1],
                        'correct_answers': row[2],
                        'accuracy': row[3]
                    })
                
                return topics
        except Exception as e:
            logger.error(f"Erro ao obter todos os tópicos: {e}")
            return []

    def report_question_problem(self, question_id: int, feedback_type: str, feedback_details: str = "") -> bool:
        """
        Salva o feedback sobre uma questão problemática e exclui a questão do banco.
        
        Args:
            question_id: ID da questão com problema
            feedback_type: Tipo de problema (muito fácil, opções óbvias, confusa, etc.)
            feedback_details: Detalhes adicionais do problema (opcional)
            
        Returns:
            bool: True se o processo foi bem-sucedido, False caso contrário
        """
        try:
            # Primeiro, recupera os dados da questão antes de excluí-la
            with self.get_db_connection('questions') as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT question, options, correct_answer, explanation FROM questions WHERE id = ?", 
                              (question_id,))
                row = cursor.fetchone()
                
                if not row:
                    logger.error(f"Questão com ID {question_id} não encontrada")
                    return False
                
                question_text, options, correct_answer, explanation = row
                
                # Salva o feedback na tabela question_feedback
                cursor.execute('''
                    INSERT INTO question_feedback 
                    (question_text, options, correct_answer, explanation, feedback_type, feedback_details)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (question_text, options, correct_answer, explanation, feedback_type, feedback_details))
                
                # Exclui a questão original
                cursor.execute("DELETE FROM questions WHERE id = ?", (question_id,))
                
                conn.commit()
                logger.info(f"Questão com ID {question_id} reportada como problemática e removida")
                return True
                
        except Exception as e:
            logger.error(f"Erro ao reportar problema com questão: {e}")
            return False 
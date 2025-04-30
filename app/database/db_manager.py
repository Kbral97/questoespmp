#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database manager for PMP Questions Generator - Flask Version
"""

import os
import sqlite3
import json
import logging
from typing import Union, Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

def get_db_path():
    """Get the path to the database file."""
    # Usar um diretório local para o ambiente Flask
    db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance')
    
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
        
        # Create database directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Setup database and tables
        self.setup_database()
    
    def get_connection(self):
        """Get a database connection."""
        return sqlite3.connect(self.questions_db)

    def create_tables(self):
        """Create necessary tables if they don't exist."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Prompts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt_text TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Chunks table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Questions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    options TEXT NOT NULL,
                    correct_answer TEXT NOT NULL,
                    explanation TEXT,
                    topic TEXT,
                    subtopic TEXT,
                    difficulty INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    question_prompt_id INTEGER,
                    answer_prompt_id INTEGER,
                    distractors_prompt_id INTEGER,
                    question_chunk_id INTEGER,
                    answer_chunk_id INTEGER,
                    distractors_chunk_id INTEGER,
                    FOREIGN KEY (question_prompt_id) REFERENCES prompts (id),
                    FOREIGN KEY (answer_prompt_id) REFERENCES prompts (id),
                    FOREIGN KEY (distractors_prompt_id) REFERENCES prompts (id),
                    FOREIGN KEY (question_chunk_id) REFERENCES chunks (id),
                    FOREIGN KEY (answer_chunk_id) REFERENCES chunks (id),
                    FOREIGN KEY (distractors_chunk_id) REFERENCES chunks (id)
                )
            ''')

            conn.commit()

    def add_prompt(self, prompt_text: str) -> int:
        """Add a new prompt and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO prompts (prompt_text) VALUES (?)',
                (prompt_text,)
            )
            conn.commit()
            return cursor.lastrowid

    def add_chunk(self, content: str) -> int:
        """Add a new chunk and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO chunks (content) VALUES (?)',
                (content,)
            )
            conn.commit()
            return cursor.lastrowid

    def add_question(self, question_data: dict) -> int:
        """Add a new question with references to prompts and chunks."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO questions (
                    question, options, correct_answer, explanation, topic, subtopic,
                    question_prompt_id, answer_prompt_id, distractors_prompt_id,
                    question_chunk_id, answer_chunk_id, distractors_chunk_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                question_data['question'],
                json.dumps(question_data['options']),
                question_data['correct_answer'],
                question_data.get('explanation', ''),
                question_data.get('topic', ''),
                question_data.get('subtopic', ''),
                question_data.get('question_prompt_id'),
                question_data.get('answer_prompt_id'),
                question_data.get('distractors_prompt_id'),
                question_data.get('question_chunk_id'),
                question_data.get('answer_chunk_id'),
                question_data.get('distractors_chunk_id')
            ))
            conn.commit()
            return cursor.lastrowid

    def get_question_with_details(self, question_id: int) -> dict:
        """Get a question with all generation details."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT q.*, 
                       qp.prompt_text as question_prompt,
                       ap.prompt_text as answer_prompt,
                       dp.prompt_text as distractors_prompt,
                       qc.content as question_chunk,
                       ac.content as answer_chunk,
                       dc.content as distractors_chunk
                FROM questions q
                LEFT JOIN prompts qp ON q.question_prompt_id = qp.id
                LEFT JOIN prompts ap ON q.answer_prompt_id = ap.id
                LEFT JOIN prompts dp ON q.distractors_prompt_id = dp.id
                LEFT JOIN chunks qc ON q.question_chunk_id = qc.id
                LEFT JOIN chunks ac ON q.answer_chunk_id = ac.id
                LEFT JOIN chunks dc ON q.distractors_chunk_id = dc.id
                WHERE q.id = ?
            ''', (question_id,))
            row = cursor.fetchone()
            if not row:
                return None

            # Convert row to dictionary
            columns = [desc[0] for desc in cursor.description]
            question_dict = dict(zip(columns, row))
            question_dict['options'] = json.loads(question_dict['options'])
            return question_dict

    def get_random_question(self) -> Optional[Dict[str, Any]]:
        """Get a random question from the database."""
        with sqlite3.connect(self.questions_db) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT 1')
            row = cursor.fetchone()
            
            if not row:
                return None
                
            return {
                'id': row[0],
                'question': row[1],
                'options': json.loads(row[2]),
                'correct_answer': row[3],
                'explanation': row[4],
                'topic': row[5],
                'subtopic': row[6],
                'difficulty': row[7]
            }

    def get_question_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific question by ID."""
        try:
            with sqlite3.connect(self.questions_db) as conn:
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
                    'options': json.loads(row[2]),
                    'correct_answer': row[3],
                    'explanation': row[4],
                    'topic': row[5],
                    'subtopic': row[6],
                    'difficulty': row[7]
                }
        except Exception as e:
            logger.error(f"Erro ao buscar questão por ID: {e}")
            return None

    def update_question_stats(self, question_id: int, correct: bool):
        """Update statistics after answering a question."""
        try:
            # Get question topic
            with sqlite3.connect(self.questions_db) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT topic FROM questions WHERE id = ?', (question_id,))
                row = cursor.fetchone()
                
                if not row:
                    logger.error(f"Questão não encontrada: {question_id}")
                    return
                    
                topic = row[0] or 'Geral'
                
                # Update statistics
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
                
        except Exception as e:
            logger.error(f"Erro ao atualizar estatísticas: {e}")

    def report_question_problem(self, question_id: int, problem_type: str, details: str = "") -> bool:
        """Report a problem with a question."""
        try:
            with sqlite3.connect(self.questions_db) as conn:
                cursor = conn.cursor()
                
                # Get question data
                cursor.execute('''
                    SELECT question, options, correct_answer, explanation 
                    FROM questions 
                    WHERE id = ?
                ''', (question_id,))
                
                row = cursor.fetchone()
                if not row:
                    logger.error(f"Questão não encontrada: {question_id}")
                    return False
                
                # Save feedback
                cursor.execute('''
                    INSERT INTO question_feedback 
                    (question_text, options, correct_answer, explanation, feedback_type, feedback_details)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (row[0], row[1], row[2], row[3], problem_type, details))
                
                # Delete question
                cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erro ao reportar problema: {e}")
            return False

    def get_prompt(self, prompt_id: int) -> dict:
        """Retorna um prompt específico"""
        try:
            with sqlite3.connect(self.questions_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, prompt_text, created_at 
                    FROM prompts 
                    WHERE id = ?
                """, (prompt_id,))
                prompt = cursor.fetchone()
                if prompt:
                    return {
                        'id': prompt[0],
                        'prompt_text': prompt[1],
                        'created_at': prompt[2]
                    }
                return None
        except Exception as e:
            logger.error(f'[GET-PROMPT] Erro ao buscar prompt: {str(e)}')
            raise

    def get_chunk(self, chunk_id: int) -> dict:
        """Retorna um chunk específico"""
        try:
            with sqlite3.connect(self.questions_db) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, content, created_at 
                    FROM chunks 
                    WHERE id = ?
                """, (chunk_id,))
                chunk = cursor.fetchone()
                if chunk:
                    return {
                        'id': chunk[0],
                        'content': chunk[1],
                        'created_at': chunk[2]
                    }
                return None
        except Exception as e:
            logger.error(f'[GET-CHUNK] Erro ao buscar chunk: {str(e)}')
            raise

    def setup_database(self):
        """Create necessary database and tables."""
        with self.get_connection() as conn:
            # Create tables
            self.create_tables()
            
            # Create question feedback table
            cursor = conn.cursor()
            cursor.execute('''
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
            
            # Create user statistics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic TEXT NOT NULL,
                    questions_answered INTEGER DEFAULT 0,
                    correct_answers INTEGER DEFAULT 0,
                    last_session TIMESTAMP,
                    UNIQUE(topic)
                )
            ''')
            
            conn.commit() 

    def delete_question(self, question_id: int) -> bool:
        """Deleta apenas a questão, mantendo prompts e chunks relacionados."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar se a questão existe
                cursor.execute('SELECT id FROM questions WHERE id = ?', (question_id,))
                if not cursor.fetchone():
                    return False
                    
                # Deletar apenas a questão
                cursor.execute('DELETE FROM questions WHERE id = ?', (question_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Erro ao deletar questão {question_id}: {str(e)}")
            return False 
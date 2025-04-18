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
    
    def setup_database(self):
        """Create necessary database and tables."""
        with sqlite3.connect(self.questions_db) as conn:
            # Questions table
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
            
            # Question feedback table
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
            
            # User statistics table
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

    def add_question(self, question_data: Dict[str, Any]) -> Optional[int]:
        """
        Add a new question to the database.
        
        Args:
            question_data (Dict[str, Any]): Dictionary containing question data with keys:
                - question: str
                - options: List[str]
                - correct_answer: str
                - explanation: str
                - topic: str
                - subtopic: str
                - difficulty: int
                
        Returns:
            Optional[int]: The ID of the newly inserted question, or None if insertion failed
        """
        try:
            with sqlite3.connect(self.questions_db) as conn:
                cursor = conn.cursor()
                
                # Convert options list to JSON string
                options_json = json.dumps(question_data.get('options', []))
                
                cursor.execute('''
                    INSERT INTO questions (
                        question,
                        options,
                        correct_answer,
                        explanation,
                        topic,
                        subtopic,
                        difficulty,
                        created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (
                    question_data.get('question', ''),
                    options_json,
                    question_data.get('correct_answer', ''),
                    question_data.get('explanation', ''),
                    question_data.get('topic', ''),
                    question_data.get('subtopic', ''),
                    question_data.get('difficulty', 1)
                ))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"Erro ao adicionar questão ao banco de dados: {e}")
            return None 
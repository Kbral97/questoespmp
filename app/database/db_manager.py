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
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class TopicSummary:
    id: int
    document_title: str
    topic: str
    summary: str
    key_points: List[Dict[str, str]]
    practical_examples: List[str]
    pmbok_references: List[str]
    domains: List[str]
    created_at: datetime

def get_db_path():
    """Get the path to the database file."""
    # Usar um diretório local para o ambiente Flask
    db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'instance')
    
    # Create directory if it doesn't exist
    os.makedirs(db_dir, exist_ok=True)
    
    db_path = os.path.join(db_dir, 'questoespmp.db')  # Alterado para usar o mesmo nome do banco
    logger.info(f"[DB-PATH] Caminho do banco: {db_path}")
    logger.info(f"[DB-PATH] Banco existe: {os.path.exists(db_path)}")
    if os.path.exists(db_path):
        logger.info(f"[DB-PATH] Tamanho do banco: {os.path.getsize(db_path)} bytes")
        logger.info(f"[DB-PATH] Permissões: {oct(os.stat(db_path).st_mode)[-3:]}")
    
    return db_path

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
        
        # Execute migrations
        self.migrate_database()
    
    def get_connection(self):
        """Get a database connection."""
        try:
            logger.info(f"[DB-CONN] Tentando conectar ao banco: {self.questions_db}")
            conn = sqlite3.connect(self.questions_db)
            logger.info("[DB-CONN] Conexão estabelecida com sucesso")
            conn.row_factory = sqlite3.Row
            return conn
        except Exception as e:
            logger.error(f"[DB-CONN] Erro ao conectar ao banco: {str(e)}")
            raise

    def create_tables(self):
        """Cria as tabelas necessárias se não existirem."""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Tabela de resumos de tópicos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS topic_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_title TEXT NOT NULL,
                topic TEXT NOT NULL,
                summary TEXT NOT NULL,
                key_points TEXT NOT NULL,
                practical_examples TEXT NOT NULL,
                pmbok_references TEXT NOT NULL,
                domains TEXT NOT NULL DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Verificar e adicionar colunas faltantes
        cursor.execute("PRAGMA table_info(topic_summaries)")
        columns = {column[1]: column for column in cursor.fetchall()}
        
        # Lista de colunas necessárias e seus tipos
        required_columns = {
            'document_title': 'TEXT NOT NULL DEFAULT "Unknown"',
            'topic': 'TEXT NOT NULL',
            'summary': 'TEXT NOT NULL',
            'key_points': 'TEXT NOT NULL DEFAULT "[]"',
            'practical_examples': 'TEXT NOT NULL DEFAULT "[]"',
            'pmbok_references': 'TEXT NOT NULL DEFAULT "[]"',
            'domains': 'TEXT NOT NULL DEFAULT "[]"',
            'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
            'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
        }
        
        # Adicionar colunas faltantes
        for column_name, column_type in required_columns.items():
            if column_name not in columns:
                logger.info(f"[DB-SETUP] Adicionando coluna {column_name} à tabela topic_summaries")
                try:
                    cursor.execute(f'''
                        ALTER TABLE topic_summaries 
                        ADD COLUMN {column_name} {column_type}
                    ''')
                    conn.commit()
                    logger.info(f"[DB-SETUP] Coluna {column_name} adicionada com sucesso")
                except Exception as e:
                    logger.error(f"[DB-SETUP] Erro ao adicionar coluna {column_name}: {str(e)}")
                    # Se a coluna já existe, ignorar o erro
                    if "duplicate column name" not in str(e).lower():
                        raise

        # Tabela de questões
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                options TEXT NOT NULL DEFAULT '[]',
                correct_answer TEXT NOT NULL,
                explanation TEXT NOT NULL,
                topic TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT DEFAULT '{}',
                summary_id_1 INTEGER,
                summary_id_2 INTEGER,
                FOREIGN KEY (summary_id_1) REFERENCES topic_summaries(id),
                FOREIGN KEY (summary_id_2) REFERENCES topic_summaries(id)
            )
        ''')

        # Tabela de uso de resumos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS summary_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                summary_id INTEGER NOT NULL,
                usage_count INTEGER DEFAULT 0,
                last_used TIMESTAMP,
                FOREIGN KEY (summary_id) REFERENCES topic_summaries(id)
            )
        ''')

        conn.commit()
        conn.close()

    def migrate_database(self):
        """Executa migrações necessárias no banco de dados."""
        logger.info("[DB-MIGRATE] Iniciando migração do banco de dados")
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Verificar se a tabela topic_summaries existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='topic_summaries'")
            if not cursor.fetchone():
                logger.info("[DB-MIGRATE] Tabela topic_summaries não encontrada, criando...")
                self.create_tables()
                return
            
            # Verificar colunas existentes
            cursor.execute("PRAGMA table_info(topic_summaries)")
            existing_columns = {column[1]: column for column in cursor.fetchall()}
            
            # Lista de colunas necessárias
            required_columns = {
                'document_title': 'TEXT NOT NULL',
                'topic': 'TEXT NOT NULL',
                'summary': 'TEXT NOT NULL',
                'key_points': 'TEXT NOT NULL',
                'practical_examples': 'TEXT NOT NULL',
                'pmbok_references': 'TEXT NOT NULL',
                'domains': 'TEXT NOT NULL',
                'created_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP',
                'updated_at': 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'
            }
            
            # Adicionar colunas faltantes
            for column_name, column_type in required_columns.items():
                if column_name not in existing_columns:
                    logger.info(f"[DB-MIGRATE] Adicionando coluna {column_name} à tabela topic_summaries")
                    try:
                        cursor.execute(f'''
                            ALTER TABLE topic_summaries 
                            ADD COLUMN {column_name} {column_type}
                        ''')
                        conn.commit()
                        logger.info(f"[DB-MIGRATE] Coluna {column_name} adicionada com sucesso")
                    except Exception as e:
                        logger.error(f"[DB-MIGRATE] Erro ao adicionar coluna {column_name}: {str(e)}")
                        # Se a coluna já existe, ignorar o erro
                        if "duplicate column name" not in str(e).lower():
                            raise
            
            # Verificar se a tabela summary_usage existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='summary_usage'")
            if not cursor.fetchone():
                logger.info("[DB-MIGRATE] Tabela summary_usage não encontrada, criando...")
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS summary_usage (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        summary_id INTEGER NOT NULL,
                        usage_count INTEGER DEFAULT 0,
                        last_used TIMESTAMP,
                        FOREIGN KEY (summary_id) REFERENCES topic_summaries(id)
                    )
                ''')
                conn.commit()
                logger.info("[DB-MIGRATE] Tabela summary_usage criada com sucesso")
            
            conn.commit()
            logger.info("[DB-MIGRATE] Migração concluída com sucesso")
            
        except Exception as e:
            logger.error(f"[DB-MIGRATE] Erro durante a migração: {str(e)}")
            raise
        finally:
            conn.close()

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
                    question, options, correct_answer, explanation, topic,
                    question_prompt_id, answer_prompt_id, distractors_prompt_id,
                    question_chunk_id, answer_chunk_id, distractors_chunk_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                question_data['question'],
                json.dumps(question_data['options']),
                question_data['correct_answer'],
                question_data.get('explanation', ''),
                question_data.get('topic', ''),
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

    def get_random_question(self):
        """Retorna uma questão aleatória do banco de dados."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Log do total de questões
                cursor.execute('SELECT COUNT(*) FROM questions')
                total_questions = cursor.fetchone()[0]
                logger.info(f"Total de questões no banco: {total_questions}")
                
                if total_questions == 0:
                    logger.warning("Nenhuma questão encontrada no banco de dados")
                    return None
                    
                cursor.execute('''
                    SELECT id, question, options, correct_answer, explanation, topic
                    FROM questions 
                    ORDER BY RANDOM() 
                    LIMIT 1
                ''')
                question = cursor.fetchone()
                
                if not question:
                    logger.warning("Nenhuma questão retornada pela query")
                    return None
                    
                # Log detalhado da questão
                logger.info(f"Questão encontrada - ID: {question['id']}")
                logger.info(f"Resposta correta original: {question['correct_answer']}")
                logger.info(f"Tipo da resposta correta: {type(question['correct_answer'])}")
                
                # Processar opções
                try:
                    options = json.loads(question['options'])
                    if not isinstance(options, list) or len(options) != 4:
                        logger.error(f"Opções inválidas para questão {question['id']}: {options}")
                        return None
                except json.JSONDecodeError as e:
                    logger.error(f"Erro ao decodificar opções da questão {question['id']}: {str(e)}")
                    return None
                    
                # Validar e converter o índice da resposta correta
                try:
                    correct_answer = int(question['correct_answer'])
                    if correct_answer < 0 or correct_answer >= len(options):
                        logger.error(f"Índice de resposta correta inválido para questão {question['id']}: {correct_answer}")
                        return None
                except (ValueError, TypeError) as e:
                    logger.error(f"Erro ao converter índice da resposta correta da questão {question['id']}: {str(e)}")
                    return None
                    
                # Log final da questão processada
                logger.info(f"Questão processada com sucesso - ID: {question['id']}")
                logger.info(f"Resposta correta final: {correct_answer}")
                logger.info(f"Número de opções: {len(options)}")
                
                return {
                    'id': question['id'],
                    'question': question['question'],
                    'options': options,
                    'correct_answer': correct_answer,
                    'explanation': question['explanation'],
                    'topic': question['topic']
                }
                
        except Exception as e:
            logger.error(f"Erro ao buscar questão aleatória: {str(e)}")
            logger.error("Stack trace:", exc_info=True)
            return None

    def get_question_by_id(self, question_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific question by ID."""
        try:
            with sqlite3.connect(self.questions_db) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, question, options, correct_answer, explanation, topic
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
                    'correct_answer': int(row[3]),
                    'explanation': row[4],
                    'topic': row[5]
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
        try:
            logger.info("[DB-SETUP] Iniciando setup do banco de dados")
            logger.info(f"[DB-SETUP] Caminho do banco: {self.questions_db}")
            
            with self.get_connection() as conn:
                # Create tables
                self.create_tables()
                
                # Verificar estrutura da tabela questions
                cursor = conn.cursor()
                cursor.execute("PRAGMA table_info(questions)")
                columns = cursor.fetchall()
                logger.info(f"[DB-SETUP] Estrutura da tabela questions: {[col[1] for col in columns]}")
                
                # Verificar se existem questões
                cursor.execute("SELECT COUNT(*) FROM questions")
                count = cursor.fetchone()[0]
                logger.info(f"[DB-SETUP] Total de questões na tabela: {count}")
                
                # Verificar algumas questões para debug
                if count > 0:
                    cursor.execute("SELECT id, question, options, correct_answer FROM questions LIMIT 5")
                    questions = cursor.fetchall()
                    logger.info(f"[DB-SETUP] Exemplo de questões: {questions}")
                
                # Recriar tabela questions se necessário
                try:
                    cursor.execute("SELECT options FROM questions LIMIT 1")
                except sqlite3.OperationalError:
                    logger.info("[DB-SETUP] Recriando tabela questions...")
                    self.recreate_questions_table()
                
                # Create question feedback table
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
                
                # Create reported questions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS reported_questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question_id INTEGER NOT NULL,
                        reason TEXT NOT NULL,
                        details TEXT,
                        reported_by INTEGER NOT NULL,
                        reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (question_id) REFERENCES questions(id),
                        FOREIGN KEY (reported_by) REFERENCES user(id)
                    )
                ''')
                
                # Verificar se as tabelas foram criadas
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                logger.info(f"[DB-SETUP] Tabelas existentes: {[table[0] for table in tables]}")
                
                # Verificar conteúdo das tabelas
                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    logger.info(f"[DB-SETUP] Tabela {table_name}: {count} registros")
                
                conn.commit()
                logger.info("[DB-SETUP] Setup do banco de dados concluído com sucesso")
                
        except Exception as e:
            logger.error(f"[DB-SETUP] Erro ao configurar banco de dados: {str(e)}")
            logger.error("[DB-SETUP] Stack trace:", exc_info=True)
            raise

    def check_database_status(self):
        """Verifica o status do banco de dados e retorna informações detalhadas."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar tabelas existentes
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                table_names = [table[0] for table in tables]
                logger.info(f"[DB-STATUS] Tabelas existentes: {table_names}")
                
                # Verificar estrutura da tabela questions
                if 'questions' in table_names:
                    cursor.execute("PRAGMA table_info(questions)")
                    columns = cursor.fetchall()
                    logger.info(f"[DB-STATUS] Estrutura da tabela questions: {[col[1] for col in columns]}")
                    
                    # Verificar total de questões
                    cursor.execute("SELECT COUNT(*) FROM questions")
                    count = cursor.fetchone()[0]
                    logger.info(f"[DB-STATUS] Total de questões: {count}")
                    
                    # Verificar algumas questões para debug
                    if count > 0:
                        cursor.execute("SELECT id, question, options, correct_answer FROM questions LIMIT 5")
                        questions = cursor.fetchall()
                        logger.info(f"[DB-STATUS] Exemplo de questões: {questions}")
                else:
                    count = 0
                
                return {
                    'tables': table_names,
                    'questions_count': count,
                    'database_path': self.questions_db,
                    'database_exists': os.path.exists(self.questions_db),
                    'database_size': os.path.getsize(self.questions_db) if os.path.exists(self.questions_db) else 0
                }
                
        except Exception as e:
            logger.error(f"[DB-STATUS] Erro ao verificar status do banco: {str(e)}")
            logger.error("[DB-STATUS] Stack trace:", exc_info=True)
            return {
                'error': str(e),
                'database_path': self.questions_db,
                'database_exists': os.path.exists(self.questions_db)
            }

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

    def find_most_relevant_chunks(self, query: str, num_chunks: int = 3) -> List[Dict]:
        """
        Encontra os chunks mais relevantes para uma query usando TF-IDF e similaridade de cosseno.
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Log do total de chunks no banco
                cursor.execute('SELECT COUNT(*) FROM chunks')
                total_chunks = cursor.fetchone()[0]
                logger.info(f"[CHUNKS-SEARCH] Total de chunks no banco: {total_chunks}")
                
                # Buscar todos os chunks
                cursor.execute('SELECT id, content, created_at FROM chunks')
                chunks = cursor.fetchall()
                
                if not chunks:
                    logger.warning("[CHUNKS-SEARCH] Nenhum chunk encontrado no banco de dados")
                    return []
                
                # Log dos primeiros chunks para debug
                logger.info(f"[CHUNKS-SEARCH] Primeiros 3 chunks no banco:")
                for i, chunk in enumerate(chunks[:3]):
                    logger.info(f"[CHUNKS-SEARCH] Chunk {i+1}:")
                    logger.info(f"[CHUNKS-SEARCH] - ID: {chunk[0]}")
                    logger.info(f"[CHUNKS-SEARCH] - Conteúdo: {chunk[1][:200]}...")
                    logger.info(f"[CHUNKS-SEARCH] - Data: {chunk[2]}")
                
                # Extrair textos para comparação
                texts = [chunk[1] for chunk in chunks]  # content
                texts.append(query)
                
                # Criar vetorizador TF-IDF com parâmetros otimizados
                vectorizer = TfidfVectorizer(
                    max_features=10000,
                    min_df=1,
                    max_df=0.9,
                    ngram_range=(1, 2)  # Considerar bigramas também
                )
                
                try:
                    tfidf_matrix = vectorizer.fit_transform(texts)
                    logger.info(f"[CHUNKS-SEARCH] Matriz TF-IDF criada com sucesso. Shape: {tfidf_matrix.shape}")
                except Exception as e:
                    logger.error(f"[CHUNKS-SEARCH] Erro ao criar matriz TF-IDF: {str(e)}")
                    return []
                
                # Calcular similaridade
                query_vector = tfidf_matrix[-1]
                similarities = cosine_similarity(query_vector, tfidf_matrix[:-1])[0]
                
                # Log das similaridades
                logger.info(f"[CHUNKS-SEARCH] Similaridades calculadas. Range: {min(similarities):.3f} - {max(similarities):.3f}")
                
                # Ordenar por similaridade
                indices = np.argsort(similarities)[::-1][:num_chunks]
                
                # Retornar chunks com scores
                relevant_chunks = []
                for idx in indices:
                    chunk_id, content, created_at = chunks[idx]
                    score = float(similarities[idx])
                    
                    # Log detalhado de cada chunk relevante
                    logger.info(f"[CHUNKS-SEARCH] Chunk {chunk_id} - Score: {score:.3f}")
                    logger.info(f"[CHUNKS-SEARCH] - Conteúdo: {content[:200]}...")
                    
                    # Só incluir chunks com score significativo
                    if score > 0.1:  # Threshold mínimo de similaridade
                        relevant_chunks.append({
                            'id': chunk_id,
                            'content': content,
                            'created_at': created_at,
                            'relevance_score': score
                        })
                    else:
                        logger.info(f"[CHUNKS-SEARCH] Chunk {chunk_id} descartado por score baixo: {score:.3f}")
                
                logger.info(f"[CHUNKS-SEARCH] Total de chunks relevantes encontrados: {len(relevant_chunks)}")
                if relevant_chunks:
                    logger.info(f"[CHUNKS-SEARCH] Scores finais: {[chunk['relevance_score'] for chunk in relevant_chunks]}")
                
                return relevant_chunks
                
        except Exception as e:
            logger.error(f"[CHUNKS-SEARCH] Erro ao buscar chunks relevantes: {str(e)}")
            logger.error("[CHUNKS-SEARCH] Stack trace:", exc_info=True)
            return [] 

    def get_all_topic_summaries(self) -> List[Dict]:
        """Retorna todos os resumos de tópicos armazenados no banco de dados"""
        try:
            query = """
            SELECT id, document_title, topic, summary, key_points, practical_examples, pmbok_references, created_at
            FROM topic_summaries
            ORDER BY created_at DESC
            """
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Log da estrutura da tabela
                cursor.execute("PRAGMA table_info(topic_summaries)")
                columns = cursor.fetchall()
                logger.info(f"[GET-SUMMARIES] Estrutura da tabela: {[col[1] for col in columns]}")
                
                # Log do total de registros
                cursor.execute("SELECT COUNT(*) FROM topic_summaries")
                total = cursor.fetchone()[0]
                logger.info(f"[GET-SUMMARIES] Total de registros: {total}")
                
                # Log dos registros existentes
                cursor.execute("SELECT id, document_title, topic FROM topic_summaries")
                rows = cursor.fetchall()
                logger.info(f"[GET-SUMMARIES] Registros encontrados: {rows}")
                
                # Executar a query principal
                cursor.execute(query)
                rows = cursor.fetchall()
                
                summaries = []
                for row in rows:
                    summary = {
                        'id': row[0],
                        'document_title': row[1],
                        'topic': row[2],
                        'summary': row[3],
                        'key_points': json.loads(row[4]) if row[4] else [],
                        'practical_examples': json.loads(row[5]) if row[5] else [],
                        'pmbok_references': json.loads(row[6]) if row[6] else [],
                        'created_at': row[7]
                    }
                    summaries.append(summary)
                
                logger.info(f"[GET-SUMMARIES] Resumos processados: {len(summaries)}")
                return summaries
                
        except Exception as e:
            logger.error(f"[GET-SUMMARIES] Erro ao buscar resumos de tópicos: {str(e)}")
            logger.error("[GET-SUMMARIES] Stack trace:", exc_info=True)
            return []

    def get_topic_summary(self, summary_id: int) -> Optional[TopicSummary]:
        """Busca um resumo de tópico pelo ID"""
        try:
            logger.info(f"[GET-SUMMARY] Buscando resumo com ID {summary_id}")
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, document_title, topic, summary, key_points, 
                           practical_examples, pmbok_references, domains, created_at
                    FROM topic_summaries 
                    WHERE id = ?
                """, (summary_id,))
                
                row = cursor.fetchone()
                if row:
                    logger.info(f"[GET-SUMMARY] Resumo encontrado: {row}")
                    return TopicSummary(
                        id=row[0],
                        document_title=row[1],
                        topic=row[2],
                        summary=row[3],
                        key_points=json.loads(row[4]) if row[4] else [],
                        practical_examples=json.loads(row[5]) if row[5] else [],
                        pmbok_references=json.loads(row[6]) if row[6] else [],
                        domains=json.loads(row[7]) if row[7] else [],
                        created_at=row[8]
                    )
                logger.info(f"[GET-SUMMARY] Nenhum resumo encontrado com ID {summary_id}")
                return None
                
        except Exception as e:
            logger.error(f"[GET-SUMMARY] Erro ao buscar resumo: {str(e)}")
            logger.error("[GET-SUMMARY] Stack trace:", exc_info=True)
            raise

    def save_topic_summary(self, document_title: str, topic: str, summary: str,
                         key_points: List[Dict[str, str]], practical_examples: List[str],
                         pmbok_references: List[str], domains: List[str] = None) -> int:
        """Salva um resumo de tópico no banco de dados"""
        try:
            logger.info("[SAVE-SUMMARY] Dados recebidos:")
            logger.info(f"[SAVE-SUMMARY] document_title: {document_title}")
            logger.info(f"[SAVE-SUMMARY] topic: {topic}")
            logger.info(f"[SAVE-SUMMARY] summary: {summary}")
            logger.info(f"[SAVE-SUMMARY] key_points: {key_points}")
            logger.info(f"[SAVE-SUMMARY] practical_examples: {practical_examples}")
            logger.info(f"[SAVE-SUMMARY] pmbok_references: {pmbok_references}")
            logger.info(f"[SAVE-SUMMARY] domains: {domains}")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar se já existe um resumo para este tópico
                cursor.execute("""
                    SELECT id FROM topic_summaries 
                    WHERE document_title = ? AND topic = ?
                """, (document_title, topic))
                
                existing = cursor.fetchone()
                if existing:
                    # Atualizar resumo existente
                    cursor.execute("""
                        UPDATE topic_summaries 
                        SET summary = ?, key_points = ?, practical_examples = ?,
                            pmbok_references = ?, domains = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (
                        summary,
                        json.dumps(key_points),
                        json.dumps(practical_examples),
                        json.dumps(pmbok_references),
                        json.dumps(domains or []),
                        existing[0]
                    ))
                    summary_id = existing[0]
                    logger.info(f"[SAVE-SUMMARY] Resumo já existe com ID: {summary_id}")
                else:
                    # Inserir novo resumo
                    cursor.execute("""
                        INSERT INTO topic_summaries (
                            document_title, topic, summary, key_points,
                            practical_examples, pmbok_references, domains
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        document_title,
                        topic,
                        summary,
                        json.dumps(key_points),
                        json.dumps(practical_examples),
                        json.dumps(pmbok_references),
                        json.dumps(domains or [])
                    ))
                    summary_id = cursor.lastrowid
                    logger.info(f"[SAVE-SUMMARY] Novo resumo salvo com ID: {summary_id}")
                
                conn.commit()
                
                # Buscar o resumo salvo para log
                cursor.execute("""
                    SELECT * FROM topic_summaries WHERE id = ?
                """, (summary_id,))
                saved_data = cursor.fetchone()
                logger.info(f"[SAVE-SUMMARY] Dados salvos: {saved_data}")
                
                return summary_id
                
        except Exception as e:
            logger.error(f"[SAVE-SUMMARY] Erro ao salvar resumo: {str(e)}")
            logger.error("[SAVE-SUMMARY] Stack trace:", exc_info=True)
            raise

    def get_least_used_summaries_by_domain(self, domain: str, limit: int = 2) -> List[Dict]:
        """
        Busca os resumos menos utilizados para um determinado domínio.
        
        Args:
            domain: Nome do domínio
            limit: Número de resumos a retornar
            
        Returns:
            Lista de dicionários contendo os resumos
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Busca resumos que contêm o domínio especificado
        cursor.execute('''
            SELECT ts.id, ts.summary, ts.key_points, ts.practical_examples, 
                   ts.pmbok_references, ts.domains, COALESCE(su.usage_count, 0) as usage_count
            FROM topic_summaries ts
            LEFT JOIN summary_usage su ON ts.id = su.summary_id
            WHERE ts.domains LIKE ?
            ORDER BY usage_count ASC, ts.created_at DESC
            LIMIT ?
        ''', (f'%{domain}%', limit))
        
        results = cursor.fetchall()
        conn.close()
        
        return [{
            'id': row[0],
            'summary': row[1],
            'key_points': json.loads(row[2]),
            'practical_examples': json.loads(row[3]),
            'pmbok_references': json.loads(row[4]),
            'domains': json.loads(row[5]),
            'usage_count': row[6]
        } for row in results]

    def update_summary_usage(self, summary_id: int):
        """
        Atualiza o contador de uso de um resumo.
        
        Args:
            summary_id: ID do resumo
        """
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Verifica se já existe um registro para este resumo
        cursor.execute('''
            INSERT INTO summary_usage (summary_id, usage_count, last_used)
            VALUES (?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(summary_id) DO UPDATE SET
                usage_count = usage_count + 1,
                last_used = CURRENT_TIMESTAMP
        ''', (summary_id,))
        
        conn.commit()
        conn.close()

    def save_question(self, question_data: dict) -> int:
        """Salva uma nova questão no banco de dados."""
        try:
            logger.info("[SAVE-QUESTION] Iniciando salvamento de questão")
            logger.info(f"[SAVE-QUESTION] Dados recebidos: {question_data}")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Validar campos obrigatórios
                required_fields = ['question', 'options', 'correct_answer', 'explanation', 'topic']
                missing_fields = [field for field in required_fields if not question_data.get(field)]
                
                if missing_fields:
                    logger.error(f"[SAVE-QUESTION] Campos obrigatórios ausentes: {missing_fields}")
                    raise ValueError(f"Campos obrigatórios ausentes: {missing_fields}")
                
                # Validar tipos de dados
                if not isinstance(question_data['options'], list):
                    logger.error(f"[SAVE-QUESTION] Campo options não é um array: {question_data['options']}")
                    raise ValueError("Campo options deve ser um array")
                
                # Converter correct_answer para inteiro
                try:
                    correct_answer = int(question_data['correct_answer'])
                    logger.info(f"[SAVE-QUESTION] correct_answer convertido para inteiro: {correct_answer}")
                except (ValueError, TypeError) as e:
                    logger.error(f"[SAVE-QUESTION] Erro ao converter correct_answer para inteiro: {str(e)}")
                    raise ValueError("Campo correct_answer deve ser um número")
                
                # Preparar dados para inserção
                options_json = json.dumps(question_data['options'])
                metadata_json = json.dumps(question_data.get('metadata', {}))
                
                logger.info("[SAVE-QUESTION] Executando inserção no banco")
                cursor.execute('''
                    INSERT INTO questions (
                        question, options, correct_answer, explanation, 
                        topic, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    question_data['question'],
                    options_json,
                    correct_answer,  # Usar o valor convertido
                    question_data['explanation'],
                    question_data['topic'],
                    metadata_json
                ))
                
                question_id = cursor.lastrowid
                conn.commit()
                
                logger.info(f"[SAVE-QUESTION] Questão salva com ID: {question_id}")
                
                # Verificar se a questão foi salva corretamente
                cursor.execute('SELECT * FROM questions WHERE id = ?', (question_id,))
                saved_question = cursor.fetchone()
                if saved_question:
                    logger.info(f"[SAVE-QUESTION] Questão verificada no banco: {saved_question}")
                else:
                    logger.error("[SAVE-QUESTION] Questão não encontrada após salvamento")
                    raise Exception("Questão não encontrada após salvamento")
                
                return question_id
                
        except Exception as e:
            logger.error(f"[SAVE-QUESTION] Erro ao salvar questão: {str(e)}")
            logger.error("[SAVE-QUESTION] Stack trace:", exc_info=True)
            raise

    def get_questions_by_topic(self, topic):
        """Busca todas as questões de um tópico específico."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, question, options, correct_answer, explanation, topic, created_at, metadata
                    FROM questions
                    WHERE topic = ?
                ''', (topic,))
                
                questions = []
                for row in cursor.fetchall():
                    question = {
                        'id': row[0],
                        'question': row[1],
                        'options': json.loads(row[2]) if row[2] else [],
                        'correct_answer': row[3],
                        'explanation': row[4],
                        'topic': row[5],
                        'created_at': row[6],
                        'metadata': json.loads(row[7]) if row[7] else {}
                    }
                    questions.append(question)
                    
                return questions
                
        except Exception as e:
            logger.error(f"Erro ao buscar questões do tópico {topic}: {str(e)}")
            return [] 

    def get_all_summaries(self) -> List[Dict]:
        """Retorna todos os resumos armazenados no banco de dados."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, document_title, topic, summary, key_points, 
                           practical_examples, pmbok_references, domains, created_at
                    FROM topic_summaries
                    ORDER BY created_at DESC
                ''')
                
                summaries = []
                for row in cursor.fetchall():
                    summary = {
                        'id': row[0],
                        'document_title': row[1],
                        'topic': row[2],
                        'summary': row[3],
                        'key_points': json.loads(row[4]) if row[4] else [],
                        'practical_examples': json.loads(row[5]) if row[5] else [],
                        'pmbok_references': json.loads(row[6]) if row[6] else [],
                        'domains': json.loads(row[7]) if row[7] else [],
                        'created_at': row[8]
                    }
                    summaries.append(summary)
                
                return summaries
                
        except Exception as e:
            logger.error(f"Erro ao buscar todos os resumos: {str(e)}")
            return [] 

    def recreate_questions_table(self):
        """Recria a tabela questions com a estrutura correta."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar se a tabela existe
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='questions'")
                if cursor.fetchone():
                    # Backup da tabela antiga
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS questions_backup AS 
                        SELECT 
                            id, 
                            question, 
                            options,
                            CASE 
                                WHEN typeof(correct_answer) = 'text' 
                                THEN CAST(UNICODE(correct_answer) - UNICODE('A') AS INTEGER)
                                ELSE CAST(correct_answer AS INTEGER)
                            END as correct_answer,
                            COALESCE(explanation, '') as explanation,
                            COALESCE(topic, '') as topic,
                            created_at,
                            COALESCE(metadata, '{}') as metadata,
                            summary_id_1,
                            summary_id_2
                        FROM questions
                    ''')
                    
                    # Drop da tabela antiga
                    cursor.execute('DROP TABLE IF EXISTS questions')
                
                # Criação da nova tabela
                cursor.execute('''
                    CREATE TABLE questions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        question TEXT NOT NULL,
                        options TEXT NOT NULL DEFAULT '[]',
                        correct_answer INTEGER NOT NULL,
                        explanation TEXT NOT NULL,
                        topic TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT DEFAULT '{}',
                        summary_id_1 INTEGER,
                        summary_id_2 INTEGER,
                        FOREIGN KEY (summary_id_1) REFERENCES topic_summaries(id),
                        FOREIGN KEY (summary_id_2) REFERENCES topic_summaries(id)
                    )
                ''')
                
                # Restauração dos dados se houver backup
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='questions_backup'")
                if cursor.fetchone():
                    cursor.execute('''
                        INSERT INTO questions (
                            id, question, options, correct_answer, explanation, 
                            topic, created_at, metadata, summary_id_1, summary_id_2
                        )
                        SELECT 
                            id, question, options, correct_answer, explanation,
                            topic, created_at, metadata, summary_id_1, summary_id_2
                        FROM questions_backup
                    ''')
                    cursor.execute('DROP TABLE questions_backup')
                
                conn.commit()
                logger.info("[DB-MIGRATION] Tabela questions recriada com sucesso")
                
        except Exception as e:
            logger.error(f"[DB-MIGRATION] Erro ao recriar tabela questions: {str(e)}")
            raise 
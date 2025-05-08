#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para migrar dados de outros bancos para o banco principal
"""

import os
import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataMigrator:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        self.instance_dir = os.path.join(self.base_dir, 'instance')
        self.data_dir = os.path.join(self.base_dir, 'data')
        self.main_db = os.path.join(self.instance_dir, 'questoespmp.db')
        
    def get_connection(self, db_path: str) -> sqlite3.Connection:
        """Estabelece conexão com o banco de dados."""
        try:
            logger.info(f"[MIGRATE] Conectando ao banco: {db_path}")
            return sqlite3.connect(db_path)
        except Exception as e:
            logger.error(f"[MIGRATE] Erro ao conectar ao banco {db_path}: {str(e)}")
            raise

    def migrate_questions(self):
        """Migra questões do questions.db para o banco principal."""
        questions_db = os.path.join(self.instance_dir, 'questions.db')
        if not os.path.exists(questions_db):
            logger.info("[MIGRATE] Banco questions.db não encontrado")
            return

        try:
            with self.get_connection(questions_db) as src_conn, \
                 self.get_connection(self.main_db) as dest_conn:
                
                # Verificar tabelas no banco de origem
                src_cursor = src_conn.cursor()
                src_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = src_cursor.fetchall()
                logger.info(f"[MIGRATE] Tabelas encontradas em questions.db: {[t[0] for t in tables]}")

                # Verificar estrutura da tabela de origem
                src_cursor.execute("PRAGMA table_info(questions)")
                src_columns = {col[1]: col for col in src_cursor.fetchall()}
                logger.info(f"[MIGRATE] Colunas em questions.db: {list(src_columns.keys())}")

                # Migrar questões
                src_cursor.execute("SELECT * FROM questions")
                questions = src_cursor.fetchall()
                logger.info(f"[MIGRATE] Encontradas {len(questions)} questões para migrar")

                dest_cursor = dest_conn.cursor()
                for question in questions:
                    try:
                        # Verificar se a questão já existe
                        dest_cursor.execute("SELECT id FROM questions WHERE question = ?", (question[1],))
                        if not dest_cursor.fetchone():
                            # Mapear campos do banco antigo para o novo
                            question_text = question[1]  # question
                            answer = question[2] if len(question) > 2 else ""  # answer
                            distractors = question[3] if len(question) > 3 else "[]"  # distractors
                            
                            # Se distractors for string, converter para JSON
                            if isinstance(distractors, str):
                                try:
                                    distractors = json.loads(distractors)
                                except:
                                    distractors = [distractors]
                            
                            dest_cursor.execute('''
                                INSERT INTO questions (
                                    question, answer, distractors, summary_id_1, summary_id_2, created_at
                                ) VALUES (?, ?, ?, ?, ?, ?)
                            ''', (
                                question_text,
                                answer,
                                json.dumps(distractors),
                                None,  # summary_id_1
                                None,  # summary_id_2
                                datetime.now()
                            ))
                            logger.info(f"[MIGRATE] Questão migrada: {question_text[:50]}...")
                    except Exception as e:
                        logger.error(f"[MIGRATE] Erro ao migrar questão: {str(e)}")
                        logger.error(f"[MIGRATE] Questão que causou o erro: {question}")

                dest_conn.commit()
                logger.info("[MIGRATE] Migração de questões concluída")

        except Exception as e:
            logger.error(f"[MIGRATE] Erro durante migração de questões: {str(e)}")
            logger.error("[MIGRATE] Stack trace:", exc_info=True)

    def migrate_user_statistics(self):
        """Migra estatísticas de usuário do user_statistics.db para o banco principal."""
        stats_db = os.path.join(self.data_dir, 'user_statistics.db')
        if not os.path.exists(stats_db):
            logger.info("[MIGRATE] Banco user_statistics.db não encontrado")
            return

        try:
            with self.get_connection(stats_db) as src_conn, \
                 self.get_connection(self.main_db) as dest_conn:
                
                # Verificar tabelas no banco de origem
                src_cursor = src_conn.cursor()
                src_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = src_cursor.fetchall()
                logger.info(f"[MIGRATE] Tabelas encontradas em user_statistics.db: {[t[0] for t in tables]}")

                # Migrar estatísticas
                src_cursor.execute("SELECT * FROM user_statistics")
                stats = src_cursor.fetchall()
                logger.info(f"[MIGRATE] Encontradas {len(stats)} estatísticas para migrar")

                dest_cursor = dest_conn.cursor()
                for stat in stats:
                    try:
                        # Verificar se a estatística já existe
                        dest_cursor.execute("SELECT id FROM user_statistics WHERE topic = ?", (stat[1],))
                        existing = dest_cursor.fetchone()
                        
                        if existing:
                            # Atualizar estatística existente
                            dest_cursor.execute('''
                                UPDATE user_statistics 
                                SET questions_answered = questions_answered + ?,
                                    correct_answers = correct_answers + ?,
                                    last_session = ?
                                WHERE topic = ?
                            ''', (stat[2], stat[3], stat[4], stat[1]))
                        else:
                            # Inserir nova estatística
                            dest_cursor.execute('''
                                INSERT INTO user_statistics (
                                    topic, questions_answered, correct_answers, last_session
                                ) VALUES (?, ?, ?, ?)
                            ''', (stat[1], stat[2], stat[3], stat[4]))
                        
                        logger.info(f"[MIGRATE] Estatística migrada para tópico: {stat[1]}")
                    except Exception as e:
                        logger.error(f"[MIGRATE] Erro ao migrar estatística: {str(e)}")

                dest_conn.commit()
                logger.info("[MIGRATE] Migração de estatísticas concluída")

        except Exception as e:
            logger.error(f"[MIGRATE] Erro durante migração de estatísticas: {str(e)}")

    def migrate_training_data(self):
        """Migra dados de treinamento do training_data.json para o banco principal."""
        training_file = os.path.join(self.data_dir, 'training_data.json')
        if not os.path.exists(training_file):
            logger.info("[MIGRATE] Arquivo training_data.json não encontrado")
            return

        try:
            with open(training_file, 'r', encoding='utf-8') as f:
                training_data = json.load(f)
            
            logger.info(f"[MIGRATE] Encontrados {len(training_data)} registros de treinamento")

            with self.get_connection(self.main_db) as conn:
                cursor = conn.cursor()
                
                # Verificar se a coluna domains existe
                cursor.execute("PRAGMA table_info(topic_summaries)")
                columns = {column[1]: column for column in cursor.fetchall()}
                
                # Se a coluna domains não existir, criar
                if 'domains' not in columns:
                    logger.info("[MIGRATE] Adicionando coluna domains à tabela topic_summaries")
                    cursor.execute('''
                        ALTER TABLE topic_summaries 
                        ADD COLUMN domains TEXT
                    ''')
                    conn.commit()
                
                for item in training_data:
                    try:
                        # Verificar se o item já existe
                        cursor.execute("SELECT id FROM topic_summaries WHERE topic = ?", (item.get('topic', ''),))
                        if not cursor.fetchone():
                            # Mapear tema para domains
                            domains = item.get('tema', [])  # Usar tema do item antigo
                            if isinstance(domains, str):
                                domains = [domains]  # Converter para lista se for string
                            
                            cursor.execute('''
                                INSERT INTO topic_summaries (
                                    document_title, topic, summary, key_points,
                                    practical_examples, pmbok_references, domains, created_at
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                item.get('document_title', 'Unknown'),
                                item.get('topic', ''),
                                item.get('summary', ''),
                                json.dumps(item.get('key_points', [])),
                                json.dumps(item.get('practical_examples', [])),
                                json.dumps(item.get('pmbok_references', [])),
                                json.dumps(domains),  # Usar o tema mapeado para domains
                                datetime.now()
                            ))
                            logger.info(f"[MIGRATE] Dado de treinamento migrado: {item.get('topic', '')[:50]}...")
                    except Exception as e:
                        logger.error(f"[MIGRATE] Erro ao migrar dado de treinamento: {str(e)}")
                        logger.error(f"[MIGRATE] Item que causou o erro: {item}")

                conn.commit()
                logger.info("[MIGRATE] Migração de dados de treinamento concluída")

        except Exception as e:
            logger.error(f"[MIGRATE] Erro durante migração de dados de treinamento: {str(e)}")
            logger.error("[MIGRATE] Stack trace:", exc_info=True)

    def run_migration(self):
        """Executa todas as migrações."""
        logger.info("[MIGRATE] Iniciando processo de migração")
        
        # Criar backup do banco principal
        backup_path = f"{self.main_db}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        try:
            with self.get_connection(self.main_db) as src_conn, \
                 self.get_connection(backup_path) as dest_conn:
                src_conn.backup(dest_conn)
            logger.info(f"[MIGRATE] Backup criado em: {backup_path}")
        except Exception as e:
            logger.error(f"[MIGRATE] Erro ao criar backup: {str(e)}")
            return

        # Executar migrações
        self.migrate_questions()
        self.migrate_user_statistics()
        self.migrate_training_data()
        
        logger.info("[MIGRATE] Processo de migração concluído")

if __name__ == "__main__":
    migrator = DataMigrator()
    migrator.run_migration() 
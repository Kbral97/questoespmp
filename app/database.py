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

def init_db():
    """Inicializa o banco de dados criando as tabelas necessárias."""
    try:
        with db_manager.get_connection() as conn:
            cursor = conn.cursor()
            
            # Log da estrutura atual da tabela
            cursor.execute("PRAGMA table_info(topic_summaries)")
            columns = cursor.fetchall()
            logger.info(f"[DB] Estrutura atual da tabela topic_summaries: {columns}")
            
            # Cria a tabela topic_summaries se não existir
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topic_summaries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_title TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    key_points TEXT,
                    domains TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(document_title, topic)
                )
            ''')
            
            # Log da estrutura após criação/verificação
            cursor.execute("PRAGMA table_info(topic_summaries)")
            columns = cursor.fetchall()
            logger.info(f"[DB] Estrutura final da tabela topic_summaries: {columns}")
            
            # Verificar se existem registros na tabela
            cursor.execute("SELECT COUNT(*) FROM topic_summaries")
            count = cursor.fetchone()[0]
            logger.info(f"[DB] Número de registros na tabela topic_summaries: {count}")
            
            # Listar alguns registros para debug
            cursor.execute("SELECT document_title, topic FROM topic_summaries LIMIT 5")
            sample_records = cursor.fetchall()
            logger.info(f"[DB] Amostra de registros na tabela topic_summaries: {sample_records}")
            
            conn.commit()
    except Exception as e:
        logger.error(f"[DB] Erro ao inicializar banco de dados: {str(e)}")
        logger.error(f"[DB] Stack trace: {traceback.format_exc()}")
        raise 
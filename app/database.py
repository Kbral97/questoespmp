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
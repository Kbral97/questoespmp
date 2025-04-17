import sqlite3
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

class DatabaseManager:
    def __init__(self):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = 'data/text_chunks.db'
        self.logger = logging.getLogger(__name__)
        self.init_database()

    def init_database(self) -> None:
        """Initialize the database and create necessary tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Tabela de chunks de texto
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS text_chunks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        chunk_number INTEGER NOT NULL,
                        raw_text TEXT NOT NULL,
                        file_name TEXT NOT NULL,
                        created_at TEXT NOT NULL
                    )
                ''')
                
                conn.commit()
                self.logger.info("Database initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Error initializing database: {str(e)}")
            raise

    def insert_chunk(self, chunk_data: Dict[str, Any]) -> bool:
        """Insert a new text chunk into the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO text_chunks 
                    (chunk_number, raw_text, file_name, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (
                    chunk_data['chunk_number'],
                    chunk_data['raw_text'],
                    chunk_data['file_name'],
                    chunk_data['created_at']
                ))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error inserting chunk: {str(e)}")
            return False

    def get_chunks(self, page: int = 1, per_page: int = 10) -> List[Dict[str, Any]]:
        """Retrieve chunks with pagination."""
        try:
            offset = (page - 1) * per_page
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, chunk_number, raw_text, file_name, created_at
                    FROM text_chunks
                    ORDER BY file_name, chunk_number
                    LIMIT ? OFFSET ?
                ''', (per_page, offset))
                
                chunks = []
                for row in cursor.fetchall():
                    chunks.append({
                        'id': row[0],
                        'chunk_number': row[1],
                        'raw_text': row[2],
                        'file_name': row[3],
                        'created_at': row[4]
                    })
                return chunks
        except Exception as e:
            self.logger.error(f"Error retrieving chunks: {str(e)}")
            return []

    def get_total_chunks(self) -> int:
        """Get the total number of chunks in the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM text_chunks')
                return cursor.fetchone()[0]
        except Exception as e:
            self.logger.error(f"Error getting total chunks: {str(e)}")
            return 0

    def remove_chunks_by_file(self, file_name: str) -> bool:
        """Remove all chunks associated with a specific file."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM text_chunks WHERE file_name = ?', (file_name,))
                conn.commit()
                return True
        except Exception as e:
            self.logger.error(f"Error removing chunks for file {file_name}: {str(e)}")
            return False

    def get_chunk_by_id(self, chunk_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve a specific chunk by its ID."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT id, chunk_number, raw_text, file_name, created_at
                    FROM text_chunks
                    WHERE id = ?
                ''', (chunk_id,))
                
                row = cursor.fetchone()
                if row:
                    return {
                        'id': row[0],
                        'chunk_number': row[1],
                        'raw_text': row[2],
                        'file_name': row[3],
                        'created_at': row[4]
                    }
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving chunk {chunk_id}: {str(e)}")
            return None 
"""Atualiza registros existentes na tabela topic_summaries"""

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime
from datetime import datetime
import os
import json

def upgrade():
    """Atualiza registros existentes"""
    # Criar engine
    db_path = os.path.join('instance', 'questoespmp.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Criar metadata
    metadata = MetaData()
    
    # Definir tabela
    topic_summaries = Table('topic_summaries', metadata,
        Column('id', Integer, primary_key=True),
        Column('document_title', String(255)),
        Column('topic', String(100)),
        Column('summary', Text),
        Column('key_points', Text),
        Column('practical_examples', Text),
        Column('pmbok_references', Text),
        Column('domains', Text),
        Column('created_at', DateTime),
        Column('updated_at', DateTime)
    )
    
    # Conectar ao banco
    conn = engine.connect()
    
    # Atualizar registros
    conn.execute(
        topic_summaries.update()
        .where(topic_summaries.c.key_points.is_(None))
        .values(
            key_points='[]',
            practical_examples='[]',
            pmbok_references='[]',
            updated_at=datetime.utcnow()
        )
    )
    
    conn.close()

def downgrade():
    """Não há downgrade necessário"""
    pass

if __name__ == '__main__':
    upgrade() 
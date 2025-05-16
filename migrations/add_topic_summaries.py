"""Adiciona a tabela topic_summaries"""

from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Text, DateTime
from datetime import datetime
import os

def upgrade():
    """Cria a tabela topic_summaries"""
    # Criar engine
    db_path = os.path.join('instance', 'questoespmp.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Criar metadata
    metadata = MetaData()
    
    # Definir tabela
    topic_summaries = Table('topic_summaries', metadata,
        Column('id', Integer, primary_key=True),
        Column('document_title', String(255), nullable=False),
        Column('topic', String(100), nullable=False),
        Column('summary', Text),
        Column('key_points', Text),
        Column('practical_examples', Text),
        Column('pmbok_references', Text),
        Column('domains', Text),
        Column('created_at', DateTime, default=datetime.utcnow),
        Column('updated_at', DateTime, default=datetime.utcnow)
    )
    
    # Criar tabela
    metadata.create_all(engine, tables=[topic_summaries])

def downgrade():
    """Remove a tabela topic_summaries"""
    # Criar engine
    db_path = os.path.join('instance', 'questoespmp.db')
    engine = create_engine(f'sqlite:///{db_path}')
    
    # Criar metadata
    metadata = MetaData()
    
    # Definir tabela
    topic_summaries = Table('topic_summaries', metadata,
        Column('id', Integer, primary_key=True)
    )
    
    # Remover tabela
    topic_summaries.drop(engine, checkfirst=True) 
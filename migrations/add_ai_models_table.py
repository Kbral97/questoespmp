"""Adiciona tabela de modelos de IA"""

from app import db
from app.models import AIModel

def upgrade():
    """Adiciona modelos padrão ao banco de dados"""
    print("Adicionando modelos padrão...")
    
    # Adicionar modelos padrão
    default_models = [
        AIModel(
            name='GPT-4 (Perguntas)',
            model_type='question',
            model_id='gpt-4',
            is_default=True
        ),
        AIModel(
            name='GPT-4 (Respostas)',
            model_type='answer',
            model_id='gpt-4',
            is_default=True
        ),
        AIModel(
            name='GPT-4 (Distratores)',
            model_type='distractor',
            model_id='gpt-4',
            is_default=True
        )
    ]
    
    for model in default_models:
        print(f"Adicionando modelo: {model.name} ({model.model_type})")
        db.session.add(model)
    
    db.session.commit()
    print("Modelos padrão adicionados com sucesso!")

def downgrade():
    """Remove a tabela de modelos de IA"""
    print("Removendo tabela de modelos de IA...")
    db.drop_all()
    print("Tabela removida com sucesso!") 
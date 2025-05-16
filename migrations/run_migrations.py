"""Executa as migrações do banco de dados"""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.append(str(root_dir))

from app import create_app, db
from migrations.add_ai_models_table import upgrade, downgrade

def main():
    """Executa as migrações"""
    try:
        print("Iniciando migrações...")
        print(f"Diretório de trabalho atual: {os.getcwd()}")
        print(f"Caminho absoluto do banco: {os.path.abspath('instance/questoespmp.db')}")
        
        # Criar aplicação Flask
        app = create_app()
        
        # Executar migrações dentro do contexto da aplicação
        with app.app_context():
            print("Criando tabelas...")
            db.create_all()
            print("Tabelas criadas com sucesso!")
            
            print("Executando upgrade...")
            upgrade()
            print("Upgrade concluído com sucesso!")
            
        print("Migrações concluídas com sucesso!")
    except Exception as e:
        print(f"Erro ao executar migrações: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main() 
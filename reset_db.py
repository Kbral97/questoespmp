import os
import time
from app import create_app, db
from app.database import init_db

def reset_database():
    """Reseta o banco de dados removendo o arquivo e recriando as tabelas"""
    app = create_app()
    
    with app.app_context():
        # Fechar todas as conexões do SQLAlchemy
        db.session.close()
        db.engine.dispose()
        
        # Remover arquivo do banco de dados se existir
        db_path = app.config['SQLALCHEMY_DATABASE_URI'].replace('sqlite:///', '')
        if os.path.exists(db_path):
            print(f"Removendo banco de dados existente: {db_path}")
            try:
                os.remove(db_path)
            except PermissionError:
                print("Aguardando liberação do arquivo...")
                time.sleep(2)  # Aguardar 2 segundos
                try:
                    os.remove(db_path)
                except PermissionError as e:
                    print(f"Erro ao remover banco de dados: {str(e)}")
                    print("Tente fechar todas as aplicações que possam estar usando o banco de dados.")
                    return
        
        # Recriar banco de dados
        print("Criando novo banco de dados...")
        init_db()
        print("Banco de dados recriado com sucesso!")

if __name__ == '__main__':
    reset_database() 
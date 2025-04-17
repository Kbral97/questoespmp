import os
import sys
from pathlib import Path

# Adicionar o diretório atual ao PYTHONPATH
sys.path.append(str(Path(__file__).parent))

from app import create_app, db
from app.models import User

def create_admin():
    # Criar a aplicação
    app = create_app()
    
    with app.app_context():
        try:
            # Verificar se já existe um usuário admin
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                # Criar usuário admin
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    password_hash='admin'  # Em produção, use hashing adequado
                )
                db.session.add(admin)
                db.session.commit()
                print('Usuário admin criado com sucesso!')
            else:
                print('Usuário admin já existe!')
        except Exception as e:
            print(f'Erro ao criar usuário admin: {e}')
            sys.exit(1)

if __name__ == '__main__':
    create_admin() 
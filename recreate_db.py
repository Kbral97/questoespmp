from app import create_app, db
from app.models import User
import os

def recreate_database():
    app = create_app()
    with app.app_context():
        # Remover o banco de dados existente
        db_path = os.path.join(app.instance_path, 'questoespmp.db')
        if os.path.exists(db_path):
            print(f"Removendo banco de dados existente: {db_path}")
            os.remove(db_path)
        
        # Criar todas as tabelas
        print("Criando novas tabelas...")
        db.create_all()
        
        # Criar usuário admin
        admin = User(
            username='admin',
            email='admin@example.com',
            is_admin=True
        )
        admin.set_password('admin123')
        
        # Adicionar ao banco
        db.session.add(admin)
        db.session.commit()
        
        print("Banco de dados recriado com sucesso!")
        print("Usuário admin criado com senha: admin123")

if __name__ == '__main__':
    recreate_database() 
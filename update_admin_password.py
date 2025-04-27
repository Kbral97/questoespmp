from app import create_app, db
from app.models import User

def update_password():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        if user:
            user.set_password('admin123')
            db.session.commit()
            print("Senha do admin atualizada para 'admin123'")
        else:
            print("Usuário admin não encontrado")

if __name__ == '__main__':
    update_password()
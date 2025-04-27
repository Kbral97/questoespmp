from werkzeug.security import check_password_hash
from app import create_app, db
from app.models import User

def check_password():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        if user:
            print(f"Username: {user.username}")
            print(f"Password hash: {user.password_hash}")
            print(f"Check password 'admin123': {check_password_hash(user.password_hash, 'admin123')}")
        else:
            print("User not found")

if __name__ == '__main__':
    check_password()

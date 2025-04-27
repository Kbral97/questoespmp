from app import create_app, db
from app.models import User

def check_db():
    app = create_app()
    with app.app_context():
        print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])
        print("Tables:", db.engine.table_names())
        print("Users:", User.query.all())

if __name__ == '__main__':
    check_db()

from app import create_app, db
from app.models import User
from sqlalchemy import inspect
import sqlite3
import os

def check_db():
    app = create_app()
    with app.app_context():
        print("Database URI:", app.config['SQLALCHEMY_DATABASE_URI'])
        print("Tables:", db.engine.table_names())
        print("Users:", User.query.all())
        inspector = inspect(db.engine)
        print("Tables:", inspector.get_table_names())

def check_table_structure():
    db_path = os.path.join('instance', 'questoespmp.db')
    if not os.path.exists(db_path):
        print(f"Database file not found at: {db_path}")
        return

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get table info
        cursor.execute("PRAGMA table_info(topic_summaries)")
        columns = cursor.fetchall()
        
        print("\nTable Structure:")
        print("----------------")
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}")
            
        # Get sample data
        cursor.execute("SELECT * FROM topic_summaries LIMIT 1")
        sample = cursor.fetchone()
        
        if sample:
            print("\nSample Data:")
            print("------------")
            for i, col in enumerate(columns):
                print(f"{col[1]}: {sample[i]}")
        else:
            print("\nNo data found in table")
            
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    check_table_structure()

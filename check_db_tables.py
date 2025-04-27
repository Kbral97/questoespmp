import sqlite3
import os

DB_PATH = os.path.join('instance', 'questoespmp.db')

if not os.path.exists(DB_PATH):
    print(f"Arquivo de banco de dados não encontrado: {DB_PATH}")
    exit(1)

try:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    print(f"Tabelas no banco de dados {DB_PATH}:")
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    if not tables:
        print("Nenhuma tabela encontrada.")
    else:
        for table in tables:
            print(f"- {table[0]}")
    conn.close()
except Exception as e:
    print(f"Erro ao acessar o banco de dados: {e}") 
import sqlite3
import json

def check_tables():
    conn = sqlite3.connect('instance/questoespmp.db')
    cursor = conn.cursor()
    
    # Lista todas as tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    print("\nTabelas existentes:")
    for table in tables:
        print(f"\nTabela: {table[0]}")
        # Obtém a estrutura da tabela
        cursor.execute(f"PRAGMA table_info({table[0]})")
        columns = cursor.fetchall()
        print("Colunas:")
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        # Conta registros
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"Total de registros: {count}")
        
        # Se for text_chunk ou text_chunks, mostra alguns registros
        if table[0] in ['text_chunk', 'text_chunks']:
            cursor.execute(f"SELECT * FROM {table[0]} LIMIT 1")
            row = cursor.fetchone()
            if row:
                print("\nExemplo de registro:")
                for col, val in zip(columns, row):
                    print(f"  {col[1]}: {val}")
    
    conn.close()

if __name__ == "__main__":
    check_tables() 
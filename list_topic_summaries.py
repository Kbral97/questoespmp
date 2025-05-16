import sqlite3
import json

conn = sqlite3.connect('instance/questoespmp.db')
cursor = conn.cursor()

cursor.execute("SELECT * FROM topic_summaries WHERE id=2;")
row = cursor.fetchone()

if row:
    print(f"ID: {row[0]}")
    print(f"Documento: {row[1]}")
    print(f"Tópico: {row[2]}")
    print(f"Resumo: {row[3]}")
    print(f"Pontos-chave: {row[4]}")
    print(f"Exemplos práticos: {row[5]}")
    print(f"Referências PMBOK: {row[6]}")
    print(f"Domains: {row[7]}")
    print(f"Criado em: {row[8]}")
else:
    print("Registro com ID 2 não encontrado.")

conn.close() 
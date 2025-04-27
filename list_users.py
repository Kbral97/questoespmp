import sqlite3
conn = sqlite3.connect('instance/questoespmp.db')
cursor = conn.cursor()
cursor.execute("SELECT id, username, password_hash FROM user")
for row in cursor.fetchall():
    print(row)
conn.close() 
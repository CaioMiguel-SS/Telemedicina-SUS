#reseta o banco de dados apagando todos os pacientes e consultas
import sqlite3

DB_PATH = "clinica.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()
cursor.execute("DELETE FROM consulta")
cursor.execute("DELETE FROM pacientes")

conn.commit()
conn.close()

print("✅ Todos os pacientes (e consultas associadas) foram apagados!")

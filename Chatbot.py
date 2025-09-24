import os
import sqlite3
import google.generativeai as genai
from datetime import datetime

# CONFIGURAÇÃO DO GEMINI
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("API key not found. Please set the GOOGLE_API_KEY environment variable.")
genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel("gemini-2.5-flash")

system_prompt = (
    "Você é um assistente de Saúde em IA. "
    "Seu papel é coletar informações básicas (Nome, Idade, CEP, Numero de celular e os Sintomas do paciente) "
    "Porém, NÃO peça essas informações você mesmo, somente comente e dê conselhos baseados nos dados do paciente. "
    "Depois que todas as informações forem coletadas, dê um resumo das mesmas "
    "E envie esse link para o paciente: https://meet.google.com/ovr-ocwa-mxi."
)


chat = model.start_chat(history=[{"role": "user", "parts": [system_prompt]}])

# BANCO DE DADOS SQLITE
DB_PATH = r"C:\Users\Willian\Desktop\ProjetoSUS\banco-de-dados\clinica.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialogos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            autor TEXT,
            mensagem TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            idade TEXT,
            endereco TEXT,
            telefone TEXT,
            sintomas TEXT,
            data_registro TEXT
        )
    """)
    conn.commit()
    conn.close()

def salvar_dialogo(autor, mensagem):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO dialogos (timestamp, autor, mensagem) VALUES (?, ?, ?)",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), autor, mensagem)
    )
    conn.commit()
    conn.close()

def salvar_paciente(dados):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO pacientes (nome, idade, endereco, telefone, sintomas, data_registro) VALUES (?, ?, ?, ?, ?, ?)",
        (dados.get("nome"), dados.get("idade"), dados.get("endereco"),
         dados.get("telefone"), dados.get("sintomas"),
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()
    print("✅ Dados do paciente salvos no banco!")

init_db()

# COLETA GUIADA DINÂMICA
campos = [
    ('nome', "Qual é o seu nome?"),
    ('idade', "Qual é a sua idade?"),
    ('endereco', "Qual é o seu endereço?"),
    ('telefone', "Qual é o seu telefone?"),
    ('sintomas', "Quais são os seus sintomas?")
]

print("🤖 Chatbot rodando. Digite 'sair' a qualquer momento para encerrar.\n")
print("Sou seu assistente de saúde. Vou fazer algumas perguntas para entender melhor sua situação.\n")
paciente = {}

for chave, pergunta in campos:
    while True:
        user = input(f"{pergunta}\nVocê: ")
        if not user.strip():
            print("Por favor, digite alguma coisa.")
            continue
        if user.lower() in {"sair", "exit", "quit"}:
            print("Encerrando por aqui. Cuide-se!")
            salvar_dialogo("Sistema", "Sessão encerrada pelo usuário.")
            exit()

        salvar_dialogo("Usuário", user)
        paciente[chave] = user

        # Resposta do assistente
        response = chat.send_message(user)
        ai_message = response.text or "Desculpe, não consegui gerar uma resposta."
        print("Assistente:", ai_message)
        salvar_dialogo("Assistente", ai_message)
        break  # vai para próxima pergunta

# Salva paciente completo
salvar_paciente(paciente)
print("\n✅ Coleta finalizada! Todos os dados foram salvos.")

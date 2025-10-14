import os
import sqlite3
import re
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
    "Seu papel é coletar informações básicas (Nome, Idade, CEP, Numero de celular e os Sintomas do paciente). "
    "Porém, NÃO peça essas informações você mesmo, apenas comente e dê conselhos baseados nos dados do paciente. "
    "Depois que todas as informações forem coletadas, dê um resumo das mesmas "
    "e envie esse link para o paciente: https://meet.google.com/ovr-ocwa-mxi."
)

chat = model.start_chat(history=[{"role": "user", "parts": [system_prompt]}])

# BANCO DE DADOS SQLITE
DB_PATH = r"banco-de-dados\clinica.db"
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

# VALIDAÇÕES DE DADOS
def validar_nome(nome):
    return len(nome.strip()) >= 2 and all(c.isalpha() or c.isspace() for c in nome)

def validar_idade(idade):
    return idade.isdigit() and 0 < int(idade) < 120

def validar_endereco(endereco):
    return len(endereco.strip()) > 5

def validar_telefone(telefone):
    return re.fullmatch(r'\(?\d{2}\)?\s?\d{4,5}-?\d{4}', telefone) is not None

def validar_sintomas(sintomas):
    return len(sintomas.strip()) >= 3


# COLETA GUIADA DINÂMICA
campos = [
    ('nome', "Qual é o seu nome?", validar_nome, "Por favor, digite um nome válido."),
    ('idade', "Qual é a sua idade?", validar_idade, "Por favor, insira uma idade válida entre 1 e 119."),
    ('endereco', "Qual é o seu endereço?", validar_endereco, "Endereço muito curto. Tente novamente."),
    ('telefone', "Qual é o seu telefone?", validar_telefone, "Por favor, insira um telefone no formato válido. Ex: (11) 91234-5678"),
    ('sintomas', "Quais são os seus sintomas?", validar_sintomas, "Por favor, descreva ao menos brevemente seus sintomas.")
]

print("🤖 Chatbot rodando. Digite 'sair' a qualquer momento para encerrar.\n")
print("Sou seu assistente de saúde. Vou fazer algumas perguntas para entender melhor sua situação.\n")

paciente = {}

for chave, pergunta, func_validar, msg_erro in campos:
    while True:
        user = input(f"{pergunta}\nVocê: ").strip()

        if not user:
            print("Por favor, digite alguma coisa.")
            continue
        if user.lower() in {"sair", "exit", "quit"}:
            print("Encerrando por aqui. Cuide-se!")
            salvar_dialogo("Sistema", "Sessão encerrada pelo usuário.")
            exit()

        if not func_validar(user):
            print(msg_erro)
            continue

        salvar_dialogo("Usuário", user)
        paciente[chave] = user

        response = chat.send_message(user)
        ai_message = response.text or "Desculpe, não consegui gerar uma resposta."
        print("Assistente:", ai_message)
        salvar_dialogo("Assistente", ai_message)
        break

# Salva paciente completo
salvar_paciente(paciente)
print("\n✅ Coleta finalizada! Todos os dados foram salvos.")

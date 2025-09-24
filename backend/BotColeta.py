from flask import Flask, request, jsonify
from dotenv import load_dotenv
load_dotenv()
import os
import sqlite3
import google.generativeai as genai
from datetime import datetime
from flask_cors import CORS
import re

# =============================
# CONFIG GEMINI
# =============================
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("API key not found. Please set the GOOGLE_API_KEY environment variable.")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel("gemini-2.5-flash")

system_prompt = (
    "Você é um assistente de Saúde em IA. "
    "Seu papel é coletar informações básicas (Nome, Idade, Endereço(rua, número), CEP, Número de celular e os Sintomas do paciente). "
    "Se algum dado estiver faltando, pergunte de forma educada. "
    "Depois que todas as informações forem coletadas, mostre os dados informados em tópicos, dê um resumo, e envie esse link para o paciente: https://meet.google.com/ovr-ocwa-mxi."
)

# Inicializa o chat com histórico inicial
chat = model.start_chat(history=[{"role": "user", "parts": [system_prompt]}])

# =============================
# BANCO SQLITE
# =============================
DB_PATH = r"banco-de-dados/clinica.db"
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Tabela de diálogos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS dialogos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            autor TEXT,
            mensagem TEXT
        )
    """)
    # Tabela de pacientes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            idade TEXT,
            endereço TEXT,
            cep TEXT,
            telefone TEXT,
            sintomas TEXT,
            data_registro TEXT
        )
    """)
    conn.commit()
    conn.close()

def salvar_dialogo(autor, mensagem):
    if not isinstance(mensagem, str):
        mensagem = str(mensagem)
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
        "INSERT INTO pacientes (nome, idade, endereço, cep, telefone, sintomas, data_registro) VALUES (?, ?, ?, ?, ?, ?)",
        (
            dados.get("nome"),
            dados.get("idade"),
            dados.get("endereço"),
            dados.get("cep"),
            dados.get("telefone"),
            dados.get("sintomas"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    )
    conn.commit()
    conn.close()
    print("✅ Dados do paciente salvos no banco!")

# Função para extrair dados da mensagem
def analisar_dados(mensagem):
    dados = {}
    nome_match = re.search(r"nome\s*[:\-]?\s*(.*)", mensagem, re.IGNORECASE)
    idade_match = re.search(r"idade\s*[:\-]?\s*(\d+)", mensagem, re.IGNORECASE)
    endereço_match = re.search(r"endereço\s*[:\-]?\s*(\d{5}-?\d{3})", mensagem, re.IGNORECASE)
    cep_match = re.search(r"cep\s*[:\-]?\s*(\d{5}-?\d{3})", mensagem, re.IGNORECASE)
    telefone_match = re.search(r"(?:telefone|celular)\s*[:\-]?\s*(\(?\d{2}\)?\s*\d{4,5}-?\d{4})", mensagem, re.IGNORECASE)
    sintomas_match = re.search(r"sintomas\s*[:\-]?\s*(.*)", mensagem, re.IGNORECASE)

    if nome_match: dados["nome"] = nome_match.group(1).strip()
    if idade_match: dados["idade"] = idade_match.group(1).strip()
    if endereço_match: dados["endereço"] = endereço_match.group(1).strip()
    if cep_match: dados["cep"] = cep_match.group(1).strip()
    if telefone_match: dados["telefone"] = telefone_match.group(1).strip()
    if sintomas_match: dados["sintomas"] = sintomas_match.group(1).strip()
    return dados

# Função para verificar se todos os dados estão completos
def dados_completos(dados):
    campos = ["nome", "idade", "endereço", "cep", "telefone", "sintomas"]
    return all(campo in dados and dados[campo] for campo in campos)

# Mantém dados do paciente em memória durante a conversa
paciente_cache = {}

init_db()

# =============================
# FLASK APP
# =============================
app = Flask(__name__)
CORS(app)

@app.route("/chat", methods=["POST"])
def chat_api():
    global paciente_cache

    data = request.json
    user_id = data.get("user_id")  # identificar paciente na sessão
    user_message = data.get("message", "")

    if not user_message:
        return jsonify({"error": "Mensagem vazia"}), 400

    salvar_dialogo("Usuário", user_message)

    # Inicializa cache do usuário se não existir
    if user_id not in paciente_cache:
        paciente_cache[user_id] = {}

    # Analisa dados fornecidos
    novos_dados = analisar_dados(user_message)
    paciente_cache[user_id].update(novos_dados)

    # Se todos os dados foram coletados, salva no banco
    if dados_completos(paciente_cache[user_id]):
        salvar_paciente(paciente_cache[user_id])
        ai_message = "Todos os seus dados foram coletados com sucesso! ✅"
        paciente_cache.pop(user_id)  # limpa cache
    else:
        # Pergunta ao Gemini sobre próximos passos
        response = chat.send_message(user_message)
        ai_message = getattr(response, "text", str(response)) if not isinstance(response, str) else response

    salvar_dialogo("Assistente", ai_message)
    return jsonify({"reply": ai_message})

@app.route("/history", methods=["GET"])
def get_history():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, autor, mensagem FROM dialogos ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([{"timestamp": ts, "autor": autor, "mensagem": msg} for ts, autor, msg in rows])

@app.route("/pacientes", methods=["GET"])
def get_pacientes():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT nome, idade, endereço, cep, telefone, sintomas, data_registro FROM pacientes")
    rows = cursor.fetchall()
    conn.close()
    return jsonify([
        {"nome": r[0], "idade": r[1], "endereço": r[2], "cep": r[3], "telefone": r[4], "sintomas": r[5], "data_registro": r[6]}
        for r in rows
    ])

if __name__ == "__main__":
    app.run(port=5000, debug=True)
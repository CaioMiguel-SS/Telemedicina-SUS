# ia_cid.py
import os
from google import genai

# Configure sua chave de API do Gemini
genai.Client(credentials=os.getenv("GOOGLE_API_KEY"))

def gerar_cid(descricao_atestado: str) -> str:
    prompt = f"""
Você é um médico especialista em CID-10.
Com base na seguinte descrição do atestado, forneça um CID e uma breve descrição clínica.

Descrição:
{descricao_atestado}

Formato:
CID: [código]
Descrição: [texto]
"""
    try:
        client = genai.Client()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )
        texto = response.text.strip()
        return texto if texto else "CID: Não identificado\nDescrição: Sem resultado."
    except Exception as e:
        return f"CID: Não identificado\nDescrição: Erro ({str(e)})"

import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
modelo = genai.GenerativeModel("models/gemini-1.5-flash-latest")

def obtener_consejo(prompt_usuario, contexto_datos):
    system_prompt = "Eres un entrenador experto en fisiología femenina. Responde claro y útil."
    prompt_completo = f"{system_prompt}\n\nContexto:\n{contexto_datos}\n\nPregunta:\n{prompt_usuario}"
    res = modelo.generate_content(prompt_completo)
    return res.text

def procesar_nota_fuerza(texto):
    prompt = f"Eres experto biomecánico. Analiza esta nota y devuelve SOLO un JSON (lista de objetos) con: ejercicio, peso, series, repeticiones, musculo_principal, rpe (esfuerzo 1-10). Texto: {texto}"
    res = modelo.generate_content(prompt)
    try:
        # Limpiamos la respuesta por si la IA pone Markdown
        txt = res.text.replace('```json', '').replace('```', '').strip()
        return json.loads(txt)
    except:
        return []

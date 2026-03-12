import google.generativeai as genai
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Configuración ultra-simple
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Usamos 'gemini-pro', que es el nombre más estable y universal
modelo = genai.GenerativeModel("gemini-pro")

def obtener_consejo(prompt_usuario, contexto_datos):
    try:
        prompt_completo = f"Eres un entrenador experto en fisiología femenina.\nContexto: {contexto_datos}\nPregunta: {prompt_usuario}"
        # Cambiamos generate_text por generate_content (estándar actual)
        res = modelo.generate_content(prompt_completo)
        return res.text
    except Exception as e:
        return f"Error en Consultorio: {str(e)}"

def procesar_nota_fuerza(texto):
    prompt = (
        f"Analiza esta nota de gimnasio y devuelve SOLO un JSON (lista de objetos) "
        f"con las llaves: ejercicio, peso, series, repeticiones, musculo_principal, rpe. "
        f"Texto: {texto}"
    )
    try:
        res = modelo.generate_content(prompt)
        # Limpieza de markdown por si la IA se pone creativa
        txt = res.text.replace('```json', '').replace('```', '').strip()
        return json.loads(txt)
    except Exception as e:
        print(f"Error procesando nota: {e}")
        return []

import google.generativeai as genai
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configurar la API de Gemini
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Error: GEMINI_API_KEY no está configurada en el archivo .env.")
genai.configure(api_key=API_KEY)

# Inicializar el modelo
modelo = genai.GenerativeModel("gemini-1.5-flash")

def obtener_consejo(prompt_usuario, contexto_datos):
    """
    Genera un consejo basado en el prompt del usuario y el contexto de datos.
    """
    system_prompt = (
        "Eres un entrenador experto en fisiología femenina, especializado en ayudar a atletas "
        "a mejorar su rendimiento y alcanzar un ritmo de 5:00 min/km. Responde de manera clara y útil."
    )
    prompt_completo = f"{system_prompt}\n\nContexto del usuario:\n{contexto_datos}\n\nPregunta del usuario:\n{prompt_usuario}"
    respuesta = modelo.generate_text(prompt=prompt_completo)
    return respuesta.text
def procesar_nota_fuerza(texto_nota):
    """
    Procesa una nota de entrenamiento de fuerza utilizando la API de Gemini.
    """
    prompt = (
        "Extrae los ejercicios de fuerza de este texto y devuélvelos en formato JSON "
        "(una lista de objetos con: ejercicio, peso, series, repeticiones, grupo_muscular). "
        "Si no se especifica grupo muscular, asígnalo tú (ej: Hip Thrust -> Glúteos). "
        f"Texto: {texto_nota}"
    )
    respuesta = modelo.generate_text(prompt=prompt)
    try:
        return eval(respuesta.text)  # Convertir el JSON devuelto a una lista de Python
    except Exception as e:
        raise ValueError(f"Error al procesar la respuesta de Gemini: {e}")

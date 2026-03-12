import google.generativeai as genai
import os
import csv
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# 🚀 TRUCO SENIOR: Auto-detectar el modelo que funcione
nombre_modelo = "gemini-1.5-flash" # Por si acaso
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name:
        nombre_modelo = m.name
        break # Cogemos el primero que funcione y salimos

print(f"✅ Conectado al modelo: {nombre_modelo}")
modelo = genai.GenerativeModel(nombre_modelo)

def procesar_nota_fuerza(texto):
    prompt = f"CSV estricto (;). Cabecera: ejercicio;peso;series;repeticiones;grupo_muscular;musculo_principal;rpe\nREGLA VITAL: Infiere la anatomía. grupo_muscular = 'Tren Superior', 'Tren Inferior' o 'Core'. musculo_principal = lista de todos los músculos implicados (ej: Cuádriceps, Glúteos, Isquios, Core). Devuelve solo CSV.\nTexto: '{texto}'"
    try:
        txt = modelo.generate_content(prompt).text.replace('```csv', '').replace('```', '').strip()
        import csv
        return {"exito": True, "datos": [f for f in csv.DictReader(txt.split('\n'), delimiter=';')], "raw": txt}
    except Exception as e: return {"exito": False, "datos": [], "raw": str(e)}

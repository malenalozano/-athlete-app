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


def ajustar_plan_con_feedback(plan_csv, feedback, perfil_resumen=""):
    """
    Recibe el plan actual (como texto CSV con cabecera) y feedback en lenguaje natural.
    Devuelve el mismo CSV con los cambios solicitados aplicados.
    """
    prompt = (
        "Eres una entrenadora de alto rendimiento. Te doy el plan de entrenamiento semanal de una atleta en formato CSV "
        "(separador ;) y su feedback sobre cambios que desea.\n"
        "Aplica solo los cambios pedidos. No modifiques lo que no se mencione. "
        "Devuelve el plan completo actualizado SIN texto extra, solo CSV con cabecera.\n"
        f"Perfil atleta: {perfil_resumen}\n"
        f"Plan actual:\n{plan_csv}\n\n"
        f"Feedback de la atleta: {feedback}"
    )
    try:
        txt = modelo.generate_content(prompt).text
        txt = txt.replace('```csv', '').replace('```', '').strip()
        import csv, io
        reader = csv.DictReader(io.StringIO(txt), delimiter=';')
        filas = list(reader)
        if filas:
            return {"exito": True, "datos": filas, "raw": txt}
        return {"exito": False, "datos": [], "raw": txt}
    except Exception as e:
        return {"exito": False, "datos": [], "raw": str(e)}


def obtener_consejo(duda, contexto=""):
    prompt = (
        "Eres una entrenadora de running y fuerza para mujer atleta. "
        "Responde de forma concreta, segura y accionable en español.\n"
        f"Contexto del atleta: {contexto}\n"
        f"Pregunta: {duda}"
    )
    try:
        return modelo.generate_content(prompt).text.strip()
    except Exception as e:
        return f"No pude generar consejo ahora mismo: {e}"

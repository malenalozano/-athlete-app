import os
import re
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

_modelo = None
_gemini_disponible = False
_gemini_error = None


def _inferir_grupo_y_musculo(ejercicio, contexto=""):
    txt = f"{contexto} {ejercicio}".lower()

    if any(k in txt for k in ["dominad", "jalon", "remo", "bicep", "bícep", "tricep", "trícep", "hombro", "press militar", "predicador"]):
        return "Tren Superior", "Espalda/Biceps/Hombro"
    if any(k in txt for k in ["hip", "sentadilla", "búlgar", "bulgar", "peso muerto", "isquio", "gemelo", "prensa", "zancad", "pierna"]):
        return "Tren Inferior", "Gluteos/Cuadriceps/Isquios"
    if any(k in txt for k in ["core", "abdominal", "planch", "pallof", "anti", "and en polea"]):
        return "Core", "Core"
    if any(k in txt for k in ["carrera", "run", "rodaje", "series"]):
        return "Tren Inferior", "Cardiovascular"
    return "Tren Inferior", "Varios"


def _extraer_series_reps(linea):
    m = re.search(r"(\d+)\s*[xX]\s*(\d+)", linea)
    if m:
        return int(m.group(1)), int(m.group(2))

    m = re.search(r"(\d+)\s*series?\s*(?:de)?\s*(\d+)\s*rep", linea.lower())
    if m:
        return int(m.group(1)), int(m.group(2))

    return 0, 0


def _extraer_peso(linea):
    pesos = re.findall(r"(\d+(?:[\.,]\d+)?)\s*kg", linea.lower())
    if not pesos:
        return 0.0
    vals = []
    for p in pesos:
        try:
            vals.append(float(p.replace(",", ".")))
        except Exception:
            pass
    if not vals:
        return 0.0
    return max(vals)


def _limpiar_nombre_ejercicio(linea):
    txt = re.sub(r"\(.*?\)", "", linea).strip()
    txt = re.sub(r"\b\d+\s*[xX]\s*\d+\b", "", txt)
    txt = re.sub(r"\b\d+\s*series?\b", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\b\d+\s*rep(?:es)?\b", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\b\d+(?:[\.,]\d+)?\s*kg\b", "", txt, flags=re.IGNORECASE)
    txt = re.sub(r"\s+", " ", txt).strip(" -:;")
    return txt or "Nota libre"


def _parsear_nota_local(texto):
    lineas = [l.strip() for l in (texto or "").splitlines() if l.strip()]
    if not lineas:
        return []

    datos = []
    contexto = ""
    contexto_fecha = None
    dias_semana = {"lunes", "martes", "miercoles", "miércoles", "jueves", "viernes", "sabado", "sábado", "domingo"}
    import datetime
    for linea in lineas:
        low = linea.lower()
        if low in dias_semana:
            contexto_fecha = low
            continue
        # Detectar 'carrera hoy' y vincular Garmin
        vinculo_garmin = None
        if 'carrera' in low and 'hoy' in low:
            # Buscar actividad Garmin de hoy
            today = datetime.datetime.now().date()
            vinculo_garmin = {'tipo': 'carrera', 'fecha': today}
        # Formato esperado: ejercicio kg repes notas
        partes = linea.split()
        ejercicio = []
        peso = 0.0
        series = 0
        repes = 0
        notas = ""
        for i, p in enumerate(partes):
            if re.match(r"\d+(?:[\.,]\d+)?kg", p.lower()):
                peso = float(p.lower().replace("kg","" ).replace(",",".").strip())
                ejercicio = partes[:i]
                resto = partes[i+1:]
                break
        else:
            ejercicio = partes
            resto = []
        # Buscar series x repes
        for j, p in enumerate(resto):
            m = re.match(r"(\d+)x(\d+)", p)
            if m:
                series = int(m.group(1))
                repes = int(m.group(2))
                notas = " ".join(resto[j+1:])
                break
        else:
            notas = " ".join(resto)
        nombre_ejercicio = " ".join(ejercicio).strip()
        grupo, musculo = _inferir_grupo_y_musculo(nombre_ejercicio)
        datos.append({
            "ejercicio": nombre_ejercicio,
            "peso": round(float(peso), 2),
            "series": int(series or 1),
            "repeticiones": int(repes or 1),
            "grupo_muscular": grupo,
            "musculo_principal": musculo,
            "rpe": 6,
            "notas": notas.strip(),
            "fecha": contexto_fecha,
            "vinculo_garmin": vinculo_garmin,
        })

    return datos


def _inicializar_modelo():
    global _modelo, _gemini_disponible, _gemini_error

    if _modelo is not None or _gemini_disponible:
        return _modelo

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        _gemini_error = "Gemini no configurado: define GEMINI_API_KEY o GOOGLE_API_KEY"
        return None

    try:
        genai.configure(api_key=api_key)
        nombre_modelo = "gemini-1.5-flash"
        try:
            for m in genai.list_models():
                if "generateContent" in m.supported_generation_methods and "gemini" in m.name:
                    nombre_modelo = m.name
                    break
        except Exception:
            # Si no se puede listar modelos, seguimos con el valor por defecto.
            pass

        _modelo = genai.GenerativeModel(nombre_modelo)
        _gemini_disponible = True
        _gemini_error = None
        return _modelo
    except Exception as e:
        _gemini_error = str(e)
        _modelo = None
        _gemini_disponible = False
        return None

def procesar_nota_fuerza(texto):
    modelo = _inicializar_modelo()
    if modelo is None:
        datos_locales = _parsear_nota_local(texto)
        return {
            "exito": True,
            "datos": datos_locales,
            "raw": f"Procesado en modo local (sin IA): {_gemini_error}",
        }

    prompt = f"CSV estricto (;). Cabecera: ejercicio;peso;series;repeticiones;grupo_muscular;musculo_principal;rpe\nREGLA VITAL: Infiere la anatomía. grupo_muscular = 'Tren Superior', 'Tren Inferior' o 'Core'. musculo_principal = lista de todos los músculos implicados (ej: Cuádriceps, Glúteos, Isquios, Core). Devuelve solo CSV.\nTexto: '{texto}'"
    try:
        txt = modelo.generate_content(prompt).text.replace('```csv', '').replace('```', '').strip()
        import csv
        datos_ia = [f for f in csv.DictReader(txt.split('\n'), delimiter=';')]
        if datos_ia:
            return {"exito": True, "datos": datos_ia, "raw": txt}
        datos_locales = _parsear_nota_local(texto)
        return {"exito": True, "datos": datos_locales, "raw": "IA sin filas validas; aplicado parser local."}
    except Exception as e:
        datos_locales = _parsear_nota_local(texto)
        return {"exito": True, "datos": datos_locales, "raw": f"Fallo IA, aplicado parser local: {e}"}


def ajustar_plan_con_feedback(plan_csv, feedback, perfil_resumen=""):
    """
    Recibe el plan actual (como texto CSV con cabecera) y feedback en lenguaje natural.
    Devuelve el mismo CSV con los cambios solicitados aplicados.
    """
    modelo = _inicializar_modelo()
    if modelo is None:
        return {
            "exito": False,
            "datos": [],
            "raw": f"IA no disponible: {_gemini_error}",
        }

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
    modelo = _inicializar_modelo()
    if modelo is None:
        return "La IA no está configurada en este entorno. Configura GEMINI_API_KEY para habilitar consejos."

    system_prompt = (
        "Eres el Coach del Proyecto Athlete. Entrenas a dos atletas:\n"
        "- Malena (usuario_id=1, mujer, objetivo: Maratón). Combina running y fuerza.\n"
        "- Dani (usuario_id=2, hombre, objetivo: Ultramaratón 100km). Combina running y fuerza.\n\n"
        "REGLAS DE SEGURIDAD (no negociables, aplican siempre):\n"
        "- HRV < 50 o tendencia HRV < -5: prioriza descanso activo, sin sesiones de calidad.\n"
        "- Ratio carga aguda/crónica >= 1.5: descarga forzada, no añadir volumen.\n"
        "- Ratio carga aguda/crónica >= 1.3: evita alta intensidad ese día.\n"
        "- Lesión de impacto activa (rodilla, fascia plantar, gemelo, tobillo, tibia): "
        "sustituye carrera por cardio sin impacto.\n"
        "- Isquios lesionados: elimina sprints y series, añade excéntrico.\n"
        "- Lumbar/espalda: sin carga axial.\n"
        # ...existing code...
        "REGLAS PARA MALENA (ciclo menstrual):\n"
        "- Fase lútea: baja volumen y evita máxima intensidad.\n"
        "- Fase ovulatoria: ventana de alto rendimiento, aprovecha.\n"
        "- Fase folicular: tolerancia a intensidad moderada/alta.\n\n"
        "COMPORTAMIENTO:\n"
        "- Responde siempre en español, tono técnico pero cercano.\n"
        "- Si los datos del snapshot muestran riesgo, avísalo antes de cualquier consejo.\n"
        "- Sé conciso y accionable. No inventes datos que no estén en el snapshot.\n"
        "- Si no hay datos suficientes en el snapshot, indícalo y da un consejo general conservador."
    )

    prompt = (
        f"{system_prompt}\n\n"
        f"SNAPSHOT DE DATOS DEL ATLETA:\n{contexto}\n\n"
        f"PREGUNTA DEL ATLETA:\n{duda}"
    )
    try:
        return modelo.generate_content(prompt).text.strip()
    except Exception as e:
        return f"No pude generar consejo ahora mismo: {e}"

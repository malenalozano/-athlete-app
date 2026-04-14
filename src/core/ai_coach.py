import os
import re
from dotenv import load_dotenv
from src.db.db_manager import get_db_connection

try:
    import google.genai as genai
except Exception:
    genai = None

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


_STOP_WORDS = {
    "sola","solo","asistida","asistido","asistidas","asistidos",
    "parcial","parciales","sin","con","bilateral","unilateral",
    "terminar","terminado","pesado","ligero","mantener","subir","bajar",
}


def _limpiar_nombre_v2(linea: str) -> str:
    txt = re.sub(r'\b\d+(?:[\.,]\d+)?\s*kg\b', '', linea, flags=re.IGNORECASE)
    txt = re.sub(r'\b\d+\s*[xX]\s*\d+\b', '', txt)
    txt = re.sub(r'\b\d+\s*series?\b', '', txt, flags=re.IGNORECASE)
    txt = re.sub(r'\b\d+\s*rep(?:eticiones|es)?\b', '', txt, flags=re.IGNORECASE)
    txt = re.sub(r'\b\d+\b', '', txt)
    txt = re.sub(r'\s+', ' ', txt).strip(' -:;·')
    words = []
    for w in txt.split():
        if w.lower() in _STOP_WORDS:
            break
        words.append(w)
    return ' '.join(words).strip() or "Nota libre"


def _parsear_nota_local(texto: str, catalogo: dict | None = None) -> list:
    import datetime as dt
    import unicodedata

    lineas = [l.strip() for l in (texto or "").splitlines() if l.strip()]
    if not lineas:
        return []

    # Cargar catálogo personal (para ENRIQUECER, nunca para filtrar)
    if catalogo is None:
        catalogo = {}
        try:
            cc = get_db_connection()
            rows = cc.execute(
                "SELECT LOWER(nombre), grupo_muscular, musculo_principal, peso_actual "
                "FROM ejercicios_catalogo").fetchall()
            catalogo = {r[0]: {"grupo_muscular": r[1], "musculo_principal": r[2],
                                "peso_actual": r[3] or 0} for r in rows}
            cc.close()
        except Exception:
            catalogo = {}

    datos = []
    contexto_fecha = None
    dias_map = {
        "lunes":0,"martes":1,"miercoles":2,"miércoles":2,
        "jueves":3,"viernes":4,"sabado":5,"sábado":5,"domingo":6,
    }

    for linea in lineas:
        # Saltar separadores
        if re.match(r'^[-=_\s]+$', linea):
            continue

        low = linea.lower()
        low_n = unicodedata.normalize('NFKD', low).encode('ascii','ignore').decode('ascii')

        # Detectar día de semana (ej: "Viernes 27")
        dia_idx = None
        for dia, idx in dias_map.items():
            dn = unicodedata.normalize('NFKD', dia).encode('ascii','ignore').decode('ascii')
            if low_n.startswith(dn):
                dia_idx = idx; break
        if dia_idx is not None:
            hoy = dt.datetime.now().date()
            delta = (hoy.weekday() - dia_idx) % 7 or 7
            contexto_fecha = hoy - dt.timedelta(days=delta)
            continue

        # Detectar fecha "DD de mes [de YYYY]" (ej: "27 de marzo")
        meses_map = {"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
                     "julio":7,"agosto":8,"septiembre":9,"setiembre":9,
                     "octubre":10,"noviembre":11,"diciembre":12}
        m_fecha_txt = re.match(
            r'^(\d{1,2})\s+de\s+([a-z]+)(?:\s+de\s+(\d{4}))?',
            low_n, re.IGNORECASE)
        if m_fecha_txt:
            _d = int(m_fecha_txt.group(1))
            _mes_txt = m_fecha_txt.group(2)  # already ascii-normalized
            _m = meses_map.get(_mes_txt)
            _y = int(m_fecha_txt.group(3)) if m_fecha_txt.group(3) else dt.datetime.now().year
            if _m:
                try:
                    contexto_fecha = dt.date(_y, _m, _d)
                except ValueError:
                    pass
            continue

        # Saltar líneas de continuación tipo "X2", "X2-3"
        if re.match(r'^[xX]\d', linea.lstrip('- ')):
            continue

        # Formato "-N ejercicio …": reps explícitas al inicio
        reps_prefix = 0
        linea_t = linea
        m_pref = re.match(r'^-(\d+)\s+(.+)', linea)
        if m_pref:
            reps_prefix = int(m_pref.group(1))
            linea_t = m_pref.group(2)

        # Separar notas inline: texto después de "-" seguido de espacio, · o ,
        # Ejemplos: "dominadas 3x8- sola 2 asistidas" / "dominadas 3x8 - sola 2 asistidas"
        notas = ""
        # Operar sobre la línea sin el guion/espacio inicial para no confundir con "- ejercicio"
        prefijo_len = len(linea_t) - len(linea_t.lstrip('- '))
        cuerpo = linea_t[prefijo_len:]
        m_nota_dash = re.search(r'-\s+(.+)$', cuerpo)
        m_nota_sym  = re.search(r'[·,]\s*(.+)$', cuerpo)
        if m_nota_dash:
            notas   = m_nota_dash.group(1).strip()
            linea_t = linea_t[:prefijo_len + m_nota_dash.start()]
        elif m_nota_sym:
            notas   = m_nota_sym.group(1).strip()

        peso   = _extraer_peso(linea_t)
        series, reps = _extraer_series_reps(linea_t)
        if reps_prefix > 0 and reps == 0:
            reps = reps_prefix; series = 1

        nombre = _limpiar_nombre_v2(linea_t.lstrip('- '))
        if not nombre or nombre == "Nota libre" or len(nombre) < 2:
            continue

        grupo, musculo = _inferir_grupo_y_musculo(nombre)
        # Buscar en catálogo personal (exacto → parcial por normalización)
        nombre_norm = unicodedata.normalize('NFKD', nombre.lower()).encode('ascii','ignore').decode('ascii')
        nombre_norm = re.sub(r'[^a-z0-9]', '', nombre_norm)
        cat = catalogo.get(nombre.lower())
        if cat is None:
            for key, val in catalogo.items():
                key_norm = re.sub(r'[^a-z0-9]', '',
                    unicodedata.normalize('NFKD', key).encode('ascii','ignore').decode('ascii'))
                if key_norm == nombre_norm or key_norm in nombre_norm or nombre_norm in key_norm:
                    cat = val; break
        # Si no hay catálogo cargado (sin usuario_id), procesar igual
        # Si hay catálogo y no hay match, saltar la línea
        if catalogo and cat is None:
            continue
        if cat:
            nombre  = cat.get("nombre_oficial") or nombre
            grupo   = cat.get("grupo_muscular") or grupo
            musculo = cat.get("musculo_principal") or musculo
            if peso == 0:
                peso = cat.get("peso_actual") or 0

        datos.append({
            "ejercicio":        nombre,
            "peso":             round(float(peso or 0), 2),
            "series":           int(series or 1),
            "repeticiones":     int(reps or 1),
            "grupo_muscular":   grupo,
            "musculo_principal": musculo,
            "rpe":              6,
            "notas":            notas,
            "fecha":            contexto_fecha,
        })

    return datos


class _GeminiModel:
    """Thin wrapper around google.genai client to match the old generate_content(.text) API."""
    def __init__(self, client, model_name):
        self._client = client
        self._model_name = model_name

    def generate_content(self, prompt):
        return self._client.models.generate_content(model=self._model_name, contents=prompt)


def _inicializar_modelo():
    global _modelo, _gemini_disponible, _gemini_error

    if _modelo is not None or _gemini_disponible:
        return _modelo

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        _gemini_error = "Gemini no configurado: define GEMINI_API_KEY o GOOGLE_API_KEY"
        return None

    if genai is None:
        _gemini_error = "Gemini no disponible: falta el paquete google.genai"
        return None

    try:
        client = genai.Client(api_key=api_key)
        nombre_modelo = "gemini-1.5-flash"
        try:
            for m in client.models.list():
                if hasattr(m, "name") and "gemini" in m.name:
                    nombre_modelo = m.name
                    break
        except Exception:
            pass

        _modelo = _GeminiModel(client, nombre_modelo)
        _gemini_disponible = True
        _gemini_error = None
        return _modelo
    except Exception as e:
        _gemini_error = str(e)
        _modelo = None
        _gemini_disponible = False
        return None

def cargar_biblioteca_ejercicios(usuario_id: int) -> str:
    """
    Genera el bloque de contexto de ejercicios conocidos para el prompt de la IA.
    Formato: "- Nombre (también: alias1, alias2) → Grupo, Músculo"
    """
    try:
        import json as _json
        cc = get_db_connection()
        rows = cc.execute(
            "SELECT nombre, alias, grupo_muscular, musculo_principal "
            "FROM ejercicios_biblioteca WHERE usuario_id=? AND activo=1",
            (usuario_id,)).fetchall()
        cc.close()
    except Exception:
        return ""

    if not rows:
        return ""

    lineas = []
    for nombre, alias, grupo, musculo in rows:
        alias_str = ""
        if alias:
            try:
                aliases = _json.loads(alias)
                alias_str = f" (también: {', '.join(aliases)})"
            except Exception:
                alias_str = f" (también: {alias})"
        lineas.append(f"- {nombre}{alias_str} → {grupo or '?'}, {musculo or '?'}")

    return "Ejercicios conocidos de esta atleta:\n" + "\n".join(lineas)


def _catalogo_para_parser(usuario_id: int) -> dict:
    """Carga la biblioteca como dict {nombre_lower: {grupo, musculo}} para el parser local."""
    try:
        import json as _json
        cc = get_db_connection()
        rows = cc.execute(
            "SELECT nombre, alias, grupo_muscular, musculo_principal "
            "FROM ejercicios_biblioteca WHERE usuario_id=? AND activo=1",
            (usuario_id,)).fetchall()
        cc.close()
    except Exception:
        return {}

    resultado = {}
    for nombre, alias, grupo, musculo in rows:
        entrada = {"grupo_muscular": grupo, "musculo_principal": musculo, "peso_actual": 0,
                   "nombre_oficial": nombre}
        resultado[nombre.lower()] = entrada
        if alias:
            try:
                import json as _json
                for a in _json.loads(alias):
                    resultado[a.lower()] = entrada
            except Exception:
                pass
    return resultado


def procesar_nota_fuerza(texto: str, usuario_id: int = 0) -> dict:
    """
    Extrae ejercicios de una nota libre de entrenamiento.
    Usa la IA (Gemini) con el contexto de la biblioteca personal, o el parser local.
    """
    catalogo = _catalogo_para_parser(usuario_id)
    modelo   = _inicializar_modelo()

    if modelo is None:
        return {
            "exito": True,
            "datos": _parsear_nota_local(texto, catalogo=catalogo),
            "raw":   f"Modo local (sin IA): {_gemini_error}",
        }

    ctx_ejercicios = cargar_biblioteca_ejercicios(usuario_id) if usuario_id else ""

    prompt = f"""Eres un asistente de entrenamiento deportivo. Extrae los ejercicios de fuerza de esta nota.

{ctx_ejercicios}

NOTA DE ENTRENAMIENTO:
"{texto}"

INSTRUCCIONES:
- Devuelve SOLO JSON válido: una lista de objetos, sin texto extra.
- SOLO incluye ejercicios cuyos nombres aparezcan en la lista de ejercicios del usuario (arriba). Si el nombre escrito no corresponde a ninguno, ignora esa línea completamente.
- Usa siempre el nombre oficial tal como aparece en la lista del usuario.
- Asocia comentarios de percepción ("me he sentido débil", "mantener peso", "subir peso") al ejercicio más cercano como "notas".
- Cuando una línea tiene la forma "ejercicio NxM - texto", el texto después del " - " son NOTAS del ejercicio, no un ejercicio nuevo.
- Las líneas que empiezan por "DD de mes" (ej: "27 de marzo") son fechas, no ejercicios — ignóralas.

Formato de cada objeto:
{{
  "ejercicio": "nombre oficial o el que aparece",
  "peso": número_o_null,
  "series": número_o_null,
  "repeticiones": número_o_null,
  "grupo_muscular": "Tren Superior" | "Tren Inferior" | "Core" | "Cardio",
  "musculo_principal": "texto",
  "rpe": número_o_null,
  "notas": "texto_libre_o_null",
  "progresion": "subir" | "mantener" | "bajar" | null
}}"""

    try:
        import json as _json
        raw = modelo.generate_content(prompt).text.strip()
        raw_clean = raw.replace("```json", "").replace("```", "").strip()
        datos_ia = _json.loads(raw_clean)
        if isinstance(datos_ia, list) and datos_ia:
            return {"exito": True, "datos": datos_ia, "raw": raw_clean}
        return {"exito": True,
                "datos": _parsear_nota_local(texto, catalogo=catalogo),
                "raw": "IA devolvió lista vacía; parser local aplicado."}
    except Exception as e:
        return {"exito": True,
                "datos": _parsear_nota_local(texto, catalogo=catalogo),
                "raw": f"Fallo IA ({e}); parser local aplicado."}


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

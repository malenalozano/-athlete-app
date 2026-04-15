"""
src/core/ui_helpers_a.py
Helpers de sesión y parsing de notas de entrenamiento.
Extraído del monolito legacy (retirado).
"""

import os
from datetime import datetime, timedelta

from src.db.db_manager import get_db_connection

_LAST_USER_FILE = os.path.expanduser("~/.athlete_last_user")


# ---------------------------------------------------------------------------
# Sesión de usuario
# ---------------------------------------------------------------------------

def _leer_ultimo_usuario():
    try:
        with open(_LAST_USER_FILE, "r") as f:
            val = int(f.read().strip())
            if val in (1, 2):
                return val
    except Exception:
        pass
    return None


def _guardar_ultimo_usuario(uid):
    try:
        with open(_LAST_USER_FILE, "w") as f:
            f.write(str(uid))
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Parsing de notas de entrenamiento
# ---------------------------------------------------------------------------

def _dividir_nota_por_fechas(texto):
    """
    Divide el texto en segmentos por marcadores de día (día de semana o "DD de mes").
    Devuelve lista de (marca_encontrada, fragmento).
    Si no hay marcadores, devuelve todo como un segmento con marca=False.
    """
    import re
    dias_semana = r"(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)"
    meses = r"(?:enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|octubre|noviembre|diciembre)"

    # Patrón 1: día de semana (opcional con número)
    # Patrón 2: "DD de mes" (ej: 27 de marzo)
    patron = re.compile(
        rf"^\s*(?:({dias_semana}(?:\s+\d{{1,2}})?)|(\d{{1,2}}\s+de\s+{meses}))",
        re.IGNORECASE | re.MULTILINE
    )

    matches = list(patron.finditer(texto))
    if not matches:
        return [(False, texto)]

    segmentos = []
    for i, m in enumerate(matches):
        inicio = m.start()
        fin = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        fragmento = texto[inicio:fin].strip()
        segmentos.append((True, fragmento))
    return segmentos


def _clasificar_segmento_diario(texto):
    t = (texto or "").lower()
    kw_running = ["carrera", "running", "rodaje", "series", "intervalos", "garmin", "ritmo", "km", "kms"]
    kw_fuerza = ["sentadilla", "peso muerto", "dominadas", "jalon", "jalón", "remo", "curl", "press",
                 "hip", "bulgara", "búlgar", "predicador", "polea", "repet", "kg"]
    kw_lesion = ["dolor", "molest", "inflam", "tibia", "lesion", "lesión", "sobrecarga", "pinchazo",
                 "contractura", "me ha costado", "debil", "débil"]

    has_running = any(k in t for k in kw_running)
    has_fuerza = any(k in t for k in kw_fuerza)
    has_lesion = any(k in t for k in kw_lesion)

    if has_running and has_fuerza:
        tipo = "mixto"
    elif has_fuerza:
        tipo = "fuerza"
    elif has_running:
        tipo = "carrera"
    elif has_lesion:
        tipo = "lesion"
    else:
        tipo = "general"

    return {"tipo": tipo, "has_running": has_running, "has_fuerza": has_fuerza, "has_lesion": has_lesion}


def _extraer_nota_estado(texto):
    lineas = [l.strip() for l in (texto or "").splitlines() if l.strip()]
    claves = ["dolor", "molest", "inflam", "tibia", "lesion", "lesión", "me ha costado",
              "costado", "fatiga", "debil", "débil", "cansad"]
    notas = [l for l in lineas if any(k in l.lower() for k in claves)]
    return " | ".join(notas)[:500] if notas else ""


def _inferir_tipo_carrera(texto):
    t = (texto or "").lower()
    if any(k in t for k in ["tirada larga", "larga", "long run", "tl"]):
        return "tirada larga"
    if any(k in t for k in ["series", "interval", "400", "800", "1000", "repeticiones"]):
        return "series"
    if any(k in t for k in ["tempo", "umbral", "threshold"]):
        return "tempo"
    if any(k in t for k in ["cuestas", "cuesta", "hill"]):
        return "cuestas"
    if any(k in t for k in ["fartlek"]):
        return "fartlek"
    if any(k in t for k in ["suave", "recuperacion", "recuperación", "z2", "rodaje"]):
        return "rodaje suave"
    return "rodaje"


def _buscar_actividad_running_fecha(usuario_id, fecha_obj):
    fecha_iso = fecha_obj.strftime("%Y-%m-%d") if hasattr(fecha_obj, "strftime") else str(fecha_obj)
    conn = get_db_connection()
    try:
        q = conn.execute(
            """
            SELECT id_actividad, fecha, distancia_m, ritmo_medio
            FROM actividades_garmin
            WHERE usuario_id = ? AND fecha LIKE ?
            ORDER BY distancia_m DESC LIMIT 1
            """,
            (usuario_id, f"{fecha_iso}%"),
        ).fetchone()
        if not q:
            return None
        return {"id_actividad": q[0], "fecha": q[1], "distancia_m": q[2], "ritmo_medio": q[3]}
    except Exception:
        return None
    finally:
        conn.close()

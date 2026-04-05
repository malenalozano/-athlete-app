"""
src/core/ui_helpers_b.py
Parsing de fechas en texto libre y gestión de estudios científicos.
Extraído de src/app_legacy.py.
"""

import io
import os
import re
import importlib
import streamlit as st
from datetime import datetime, timedelta

from src.db.db_manager import get_db_connection
from src.core.ai_coach import obtener_consejo


# ---------------------------------------------------------------------------
# Parsing de fechas en texto libre
# ---------------------------------------------------------------------------

def extraer_fecha_historica(texto):
    hoy = datetime.now().date()
    if not isinstance(texto, str) or not texto.strip():
        return hoy, "Sin fecha detectada, se usa hoy"

    t = texto.lower()
    if "anteayer" in t:
        return hoy - timedelta(days=2), "Detectado 'anteayer'"
    if "ayer" in t:
        return hoy - timedelta(days=1), "Detectado 'ayer'"
    if "hoy" in t:
        return hoy, "Detectado 'hoy'"

    m_iso = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", t)
    if m_iso:
        y, m, d = map(int, m_iso.groups())
        try:
            return datetime(y, m, d).date(), "Detectada fecha YYYY-MM-DD"
        except ValueError:
            pass

    m_num = re.search(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b", t)
    if m_num:
        d, m, y = map(int, m_num.groups())
        y = y + 2000 if y < 100 else y
        try:
            return datetime(y, m, d).date(), "Detectada fecha DD/MM/YYYY"
        except ValueError:
            pass

    meses = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6,
             "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9,
             "octubre": 10, "noviembre": 11, "diciembre": 12}
    m_texto = re.search(r"\b(\d{1,2})\s+de\s+([a-záéíóú]+)(?:\s+de\s+(\d{4}))?\b", t)
    if m_texto:
        d = int(m_texto.group(1))
        mes_txt = m_texto.group(2).replace("á","a").replace("é","e").replace("í","i").replace("ó","o").replace("ú","u")
        y = int(m_texto.group(3)) if m_texto.group(3) else hoy.year
        m = meses.get(mes_txt)
        if m:
            try:
                return datetime(y, m, d).date(), "Detectada fecha 'D de mes'"
            except ValueError:
                pass

    dias = {"lunes": 0, "martes": 1, "miercoles": 2, "miércoles": 2,
            "jueves": 3, "viernes": 4, "sabado": 5, "sábado": 5, "domingo": 6}
    m_dia = re.search(r"\b(lunes|martes|miercoles|miércoles|jueves|viernes|sabado|sábado|domingo)\b(?:\s+(pasado|anterior))?", t)
    if m_dia:
        d_txt = m_dia.group(1)
        q = m_dia.group(2)
        objetivo = dias[d_txt]
        delta = (hoy.weekday() - objetivo) % 7
        if delta == 0:
            delta = 7
        if q in ("pasado", "anterior"):
            delta += 7
        return hoy - timedelta(days=delta), "Detectado día de la semana"

    return hoy, "Sin fecha clara detectada, se usa hoy"


# ---------------------------------------------------------------------------
# Estudios científicos
# ---------------------------------------------------------------------------

def extraer_texto_estudio(uploaded_file):
    nombre = (uploaded_file.name or "").lower()
    if nombre.endswith(".pdf"):
        try:
            PdfReader = importlib.import_module("pypdf").PdfReader
        except Exception:
            PdfReader = None
        if PdfReader is not None:
            reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
            return "\n".join(p.extract_text() or "" for p in reader.pages[:20]).strip()
    try:
        return uploaded_file.getvalue().decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def guardar_estudio_referencia(usuario_id, uploaded_file, categoria, resumen_manual=""):
    contenido = uploaded_file.getvalue()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", uploaded_file.name)
    directorio = os.path.join(os.getcwd(), "estudios")
    os.makedirs(directorio, exist_ok=True)
    file_path = os.path.join(directorio, f"{usuario_id}_{stamp}_{safe_name}")
    with open(file_path, "wb") as f:
        f.write(contenido)

    texto_extraido = extraer_texto_estudio(uploaded_file)
    if len(texto_extraido) > 12000:
        texto_extraido = texto_extraido[:12000]

    resumen = resumen_manual.strip()
    if not resumen and texto_extraido:
        prompt = (
            "Resume en 6-8 líneas este estudio científico para que una IA de entrenamiento "
            "pueda usarlo como contexto práctico. Extrae hallazgos accionables y limita exageraciones.\n\n"
            f"Texto:\n{texto_extraido[:5000]}"
        )
        resumen = obtener_consejo(prompt, "")

    conn = get_db_connection()
    try:
        conn.execute(
            """INSERT INTO estudios_referencia
               (usuario_id, titulo, categoria, archivo_path, resumen, texto_extraido, creado_en)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (usuario_id, uploaded_file.name, categoria, file_path,
             resumen[:4000] if resumen else None,
             texto_extraido, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )
        conn.commit()
    finally:
        conn.close()


@st.cache_data(ttl=600)
def contexto_estudios(usuario_id=None):
    conn = get_db_connection()
    try:
        if usuario_id is None:
            df = __import__("pandas").read_sql_query(
                "SELECT titulo, categoria, resumen FROM estudios_referencia ORDER BY creado_en DESC LIMIT 6", conn)
        else:
            df = __import__("pandas").read_sql_query(
                "SELECT titulo, categoria, resumen FROM estudios_referencia WHERE usuario_id IN (?, 0) ORDER BY creado_en DESC LIMIT 6",
                conn, params=(usuario_id,))
    except Exception:
        df = __import__("pandas").DataFrame()
    finally:
        conn.close()
    if df.empty:
        return ""
    return "\n".join(f"[{r['categoria']}] {r['titulo']}: {r['resumen']}" for _, r in df.iterrows())

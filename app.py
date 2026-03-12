import streamlit as st
import pandas as pd
import plotly.express as px
import os
import io
import importlib
import calendar
import re
from db_manager import get_db_connection, obtener_perfil, guardar_perfil, obtener_credenciales_garmin
from garmin_sync import sincronizar_actividades, sincronizar_actividades_inteligente, obtener_datos_sueno, guardar_sueno_db, iniciar_sesion_garmin, sincronizar_biometricos_garmin
from ai_coach import procesar_nota_fuerza, obtener_consejo
from seguridad import encriptar_password, desencriptar_password
from datetime import datetime, timedelta


# ── Persistencia de último usuario (archivo local) ────────────────────────
_LAST_USER_FILE = os.path.expanduser("~/.athlete_last_user")

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


def _column_exists(conn, table_name, column_name):
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return any(row[1] == column_name for row in rows)


def _ensure_column(conn, table_name, column_name, column_type):
    if not _column_exists(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")


# ── Dividir notas multi-día ("hoy hice X y ayer hice Y") ──────────────────
def _dividir_nota_por_fechas(texto):
    """
    Devuelve lista de (marca_temporal_str, fragmento) para cada segmento temporal
    detectado en el texto. Si solo hay una fecha o ninguna, devuelve [(None, texto)].
    """
    patron = (
        r'\b(hoy|ayer|anteayer|'
        r'(?:el\s+)?\d{1,2}\s+de\s+[a-záéíóúñ]+(?:\s+de\s+\d{4})?|'
        r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|'
        r'(?:lunes|martes|mi[eé]rcoles|jueves|viernes|s[aá]bado|domingo)(?:\s+pasado)?)\b'
    )
    matches = list(re.finditer(patron, texto, re.IGNORECASE))
    if len(matches) < 2:
        return [(None, texto)]
    segmentos = []
    for i, m in enumerate(matches):
        inicio = m.start()
        fin = matches[i + 1].start() if i + 1 < len(matches) else len(texto)
        fragmento = texto[inicio:fin].strip()
        segmentos.append((m.group(0), fragmento))
    return segmentos


# ── Plan conjunto (Malena + Dani para semana) ─────────────────────────────
def _cargar_plan_conjunto(semana_dt):
    """Devuelve DataFrame con planes de ambos usuarios para la semana indicada."""
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            """
            SELECT usuario_id, fecha, tipo, sesion, duracion_min, intensidad
            FROM plan_entrenamiento
            WHERE semana_inicio = ?
            ORDER BY fecha, usuario_id
            """,
            conn, params=(semana_dt.strftime("%Y-%m-%d"),),
        )
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df


def asegurar_tabla_plan_entrenamiento():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS plan_entrenamiento (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            semana_inicio TEXT,
            fecha TEXT,
            tipo TEXT,
            sesion TEXT,
            detalles TEXT,
            duracion_min INTEGER,
            intensidad TEXT,
            creado_en TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def asegurar_tablas_fuerza():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sesiones_fuerza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha TEXT,
            nota_original TEXT,
            resumen TEXT,
            created_at TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ejercicios_fuerza (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sesion_id INTEGER,
            ejercicio TEXT,
            peso REAL,
            series INTEGER,
            repeticiones INTEGER,
            grupo_muscular TEXT,
            musculo_principal TEXT,
            rpe INTEGER
        )
        """
    )
    conn.commit()
    conn.close()


def asegurar_tablas_premium():
    conn = get_db_connection()
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS datos_biometricos_premium (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha TEXT,
            hrv_ms REAL,
            fc_reposo INTEGER,
            fc_maxima INTEGER,
            cadencia_media REAL,
            longitud_zancada_m REAL,
            tiempo_contacto_ms REAL,
            oscilacion_vertical_cm REAL,
            sleep_score INTEGER,
            carga_aguda REAL,
            carga_cronica REAL,
            estres_vital INTEGER,
            rpe_sesion INTEGER,
            sensacion_notas TEXT,
            disponibilidad_min INTEGER,
            UNIQUE(usuario_id, fecha)
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS historial_lesiones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha_inicio TEXT,
            zona TEXT,
            tipo TEXT,
            activa INTEGER DEFAULT 1,
            notas TEXT,
            fecha_fin TEXT
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS estudios_referencia (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            titulo TEXT,
            categoria TEXT,
            archivo_path TEXT,
            resumen TEXT,
            texto_extraido TEXT,
            creado_en TEXT
        )
        """
    )
    for col_name, col_type in [
        ("training_readiness", "INTEGER"),
        ("body_battery", "INTEGER"),
        ("recovery_hours", "REAL"),
        ("spo2", "REAL"),
        ("potencia_media_w", "REAL"),
    ]:
        _ensure_column(conn, "datos_biometricos_premium", col_name, col_type)

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS datos_sueno (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            fecha TEXT,
            horas_totales REAL,
            score INTEGER,
            UNIQUE(usuario_id, fecha)
        )
        """
    )
    for col_name, col_type in [
        ("sleep_profundo_horas", "REAL"),
        ("sleep_rem_horas", "REAL"),
        ("sleep_vigilia_horas", "REAL"),
        ("despertares", "INTEGER"),
    ]:
        _ensure_column(conn, "datos_sueno", col_name, col_type)

    for col_name, col_type in [
        ("potencia_media_w", "REAL"),
        ("cadencia_media", "REAL"),
        ("longitud_zancada_m", "REAL"),
        ("tiempo_contacto_ms", "REAL"),
        ("oscilacion_vertical_cm", "REAL"),
    ]:
        _ensure_column(conn, "actividades_garmin", col_name, col_type)

    conn.commit()
    conn.close()


def _directorio_estudios():
    path = os.path.join(os.path.dirname(__file__), "uploaded_studies")
    os.makedirs(path, exist_ok=True)
    return path


def extraer_texto_estudio(uploaded_file):
    nombre = (uploaded_file.name or "").lower()
    if nombre.endswith(".pdf"):
        try:
            PdfReader = importlib.import_module("pypdf").PdfReader
        except Exception:
            PdfReader = None
        if PdfReader is not None:
            reader = PdfReader(io.BytesIO(uploaded_file.getvalue()))
            paginas = []
            for page in reader.pages[:20]:
                paginas.append(page.extract_text() or "")
            return "\n".join(paginas).strip()
    try:
        return uploaded_file.getvalue().decode("utf-8", errors="ignore").strip()
    except Exception:
        return ""


def guardar_estudio_referencia(usuario_id, uploaded_file, categoria, resumen_manual=""):
    contenido = uploaded_file.getvalue()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^a-zA-Z0-9._-]", "_", uploaded_file.name)
    file_path = os.path.join(_directorio_estudios(), f"{usuario_id}_{stamp}_{safe_name}")
    with open(file_path, "wb") as f:
        f.write(contenido)

    texto_extraido = extraer_texto_estudio(uploaded_file)
    if len(texto_extraido) > 12000:
        texto_extraido = texto_extraido[:12000]

    resumen = resumen_manual.strip()
    if not resumen and texto_extraido:
        contexto = texto_extraido[:5000]
        prompt = (
            "Resume en 6-8 líneas este estudio científico para que una IA de entrenamiento "
            "pueda usarlo como contexto práctico. Extrae hallazgos accionables y limita exageraciones.\n\n"
            f"Texto:\n{contexto}"
        )
        resumen = obtener_consejo(prompt, "")

    conn = get_db_connection()
    try:
        conn.execute(
            """
            INSERT INTO estudios_referencia (usuario_id, titulo, categoria, archivo_path, resumen, texto_extraido, creado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                usuario_id,
                uploaded_file.name,
                categoria,
                file_path,
                resumen[:4000] if resumen else None,
                texto_extraido,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        conn.commit()
    finally:
        conn.close()


@st.cache_data(ttl=600)
def contexto_estudios(usuario_id=None):
    conn = get_db_connection()
    try:
        if usuario_id is None:
            df = pd.read_sql_query(
                "SELECT titulo, categoria, resumen FROM estudios_referencia ORDER BY creado_en DESC LIMIT 6",
                conn,
            )
        else:
            df = pd.read_sql_query(
                "SELECT titulo, categoria, resumen FROM estudios_referencia WHERE usuario_id IN (?, 0) ORDER BY creado_en DESC LIMIT 6",
                conn,
                params=(usuario_id,),
            )
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    if df.empty:
        return ""
    bloques = []
    for _, row in df.iterrows():
        bloques.append(f"[{row['categoria']}] {row['titulo']}: {row['resumen']}")
    return "\n".join(bloques)


def obtener_estado_ciclo_malena():
    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            "SELECT fecha, fase_ciclo, fatiga_subjetiva, dolor_notas FROM diario_fisiologia WHERE usuario_id = 1 ORDER BY fecha",
            conn,
        )
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    if df.empty:
        return None

    df_valid = df[df["fase_ciclo"] != "No Aplica"].copy()
    if df_valid.empty:
        return None

    ciclo_df, _ = predecir_fases_ciclo(df_valid, horizonte_dias=40)
    hoy = datetime.now().date()
    fila_hoy = ciclo_df[ciclo_df["fecha"] == hoy]
    if fila_hoy.empty:
        fila_hoy = ciclo_df[ciclo_df["fecha"] >= hoy].head(1)
    if fila_hoy.empty:
        return None

    fase = fila_hoy.iloc[0]["fase_ciclo"]
    origen = fila_hoy.iloc[0]["origen"]
    proximas = ciclo_df[(ciclo_df["fecha"] >= hoy) & (ciclo_df["fase_ciclo"] == "Fase Folicular")].head(2)
    proxima_regla = None
    if not proximas.empty:
        futura = proximas.iloc[0]["fecha"]
        if futura >= hoy:
            proxima_regla = futura

    sugerencias = {
        "Fase Folicular": [
            "Buen momento para proponer planes, viajes o entrenos más exigentes juntos.",
            "Las conversaciones importantes suelen ir mejor en esta fase.",
        ],
        "Fase Ovulatoria": [
            "Buena ventana para citas, conexión y refuerzo positivo.",
            "Si entrenáis juntos, suele tolerar bien intensidad y sesiones sociales.",
        ],
        "Fase Lútea": [
            "Prioriza paciencia, validación emocional y menos fricción innecesaria.",
            "Suman mucho los mimos prácticos: cena reconfortante, masaje, bajar carga social.",
        ],
    }
    consejo = sugerencias.get(fase, ["Acompaña y ajusta el contexto según cómo se encuentre ese día."])

    return {
        "fase": fase,
        "origen": origen,
        "proxima_regla": proxima_regla,
        "consejos": consejo,
    }


def construir_checkpoints_objetivo(perfil, df_act):
    objetivo = (perfil.get("objetivo") or "").lower()
    checkpoints = []

    if "marat" in objetivo:
        checkpoints = [
            {"nombre": "5K en Sub 22:30", "dist_min": 4.6, "dist_max": 5.4, "ritmo_max": 4.5, "detalle": "Demuestra la velocidad máxima necesaria."},
            {"nombre": "10K en Sub 46:30", "dist_min": 9.2, "dist_max": 10.8, "ritmo_max": 4.65, "detalle": "Confirma umbral y capacidad de sostener el ritmo."},
            {"nombre": "Media Maratón en Sub 1h42", "dist_min": 20.0, "dist_max": 22.2, "ritmo_max": 4.84, "detalle": "Checkpoint definitivo de preparación para el ritmo de maratón."},
        ]
    elif "media" in objetivo:
        checkpoints = [
            {"nombre": "5K en Sub 23:30", "dist_min": 4.6, "dist_max": 5.4, "ritmo_max": 4.7, "detalle": "Velocidad base para media maratón sólida."},
            {"nombre": "10K en Sub 49:30", "dist_min": 9.2, "dist_max": 10.8, "ritmo_max": 4.95, "detalle": "Umbral aeróbico bien colocado."},
            {"nombre": "15K en Sub 1h16", "dist_min": 14.0, "dist_max": 16.2, "ritmo_max": 5.07, "detalle": "Confirma resistencia específica."},
        ]
    elif "trail" in objetivo:
        checkpoints = [
            {"nombre": "90 min continuos en Z2", "dist_min": 13.0, "dist_max": 30.0, "ritmo_max": 99.0, "detalle": "Tiempo sobre piernas sin colapso técnico."},
            {"nombre": "Control en bajadas", "dist_min": 8.0, "dist_max": 25.0, "ritmo_max": 99.0, "detalle": "Necesitas tolerar excéntrico y mantener técnica."},
        ]
    elif "hyrox" in objetivo:
        checkpoints = [
            {"nombre": "5K en Sub 25:00", "dist_min": 4.6, "dist_max": 5.4, "ritmo_max": 5.0, "detalle": "Base aeróbica para encadenar estaciones."},
            {"nombre": "2+ sesiones fuerza/semana", "dist_min": None, "dist_max": None, "ritmo_max": None, "detalle": "La fuerza sostenida es parte del objetivo."},
        ]
    else:
        checkpoints = [
            {"nombre": "5K en Sub 25:00", "dist_min": 4.6, "dist_max": 5.4, "ritmo_max": 5.0, "detalle": "Primer gran checkpoint de economía y ritmo."},
            {"nombre": "10K en Sub 52:00", "dist_min": 9.2, "dist_max": 10.8, "ritmo_max": 5.2, "detalle": "Sostener el ritmo sin deriva fuerte de fatiga."},
        ]

    actividades = df_act.copy() if not df_act.empty else pd.DataFrame()
    if not actividades.empty:
        actividades["km"] = actividades["distancia_m"].fillna(0) / 1000
        actividades["ritmo_min_km"] = pd.to_numeric(actividades.get("ritmo_medio"), errors="coerce")

    filas = []
    for cp in checkpoints:
        logrado = False
        mejor = None
        if not actividades.empty and cp["dist_min"] is not None:
            match = actividades[
                (actividades["km"] >= cp["dist_min"]) &
                (actividades["km"] <= cp["dist_max"]) &
                (actividades["ritmo_min_km"].notna())
            ].sort_values("ritmo_min_km")
            if not match.empty:
                mejor = float(match.iloc[0]["ritmo_min_km"])
                logrado = mejor <= cp["ritmo_max"]
        filas.append(
            {
                "checkpoint": cp["nombre"],
                "estado": "✅ Hecho" if logrado else "🟡 Pendiente",
                "detalle": cp["detalle"],
                "mejor_marca": "—" if mejor is None else f"{int(mejor)}:{int(round((mejor - int(mejor)) * 60)):02d}/km",
            }
        )
    return pd.DataFrame(filas)


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

    meses = {
        "enero": 1,
        "febrero": 2,
        "marzo": 3,
        "abril": 4,
        "mayo": 5,
        "junio": 6,
        "julio": 7,
        "agosto": 8,
        "septiembre": 9,
        "setiembre": 9,
        "octubre": 10,
        "noviembre": 11,
        "diciembre": 12,
    }
    m_texto = re.search(r"\b(\d{1,2})\s+de\s+([a-záéíóú]+)(?:\s+de\s+(\d{4}))?\b", t)
    if m_texto:
        d = int(m_texto.group(1))
        mes_txt = m_texto.group(2).replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
        y = int(m_texto.group(3)) if m_texto.group(3) else hoy.year
        m = meses.get(mes_txt)
        if m:
            try:
                return datetime(y, m, d).date(), "Detectada fecha 'D de mes'"
            except ValueError:
                pass

    dias = {
        "lunes": 0,
        "martes": 1,
        "miercoles": 2,
        "miércoles": 2,
        "jueves": 3,
        "viernes": 4,
        "sabado": 5,
        "sábado": 5,
        "domingo": 6,
    }
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


def _indices_distribuidos(total_dias):
    mapa = {
        0: [],
        1: [2],
        2: [1, 4],
        3: [1, 3, 5],
        4: [0, 2, 4, 6],
        5: [0, 2, 3, 5, 6],
        6: [0, 1, 2, 4, 5, 6],
        7: [0, 1, 2, 3, 4, 5, 6],
    }
    return mapa.get(max(0, min(7, int(total_dias))), [])


def generar_plan_semanal(perfil, datos, fecha_inicio_semana, plan_pareja=None):
    """
    Plan semanal premium: adapta cada sesión a HRV, sueño, carga aguda/crónica,
    lesiones activas, ciclo menstrual, estrés vital, RPE y dinámica de carrera.
    Si plan_pareja (DataFrame) se proporciona, intenta hacer coincidir días de
    entrenamiento activo con los días que la pareja también tiene sesión.
    Devuelve (DataFrame, lista_de_alertas).
    """
    # ── Perfil ────────────────────────────────────────────────────────────
    dias_carrera = int(perfil.get("carrera") or 3)
    dias_fuerza  = int(perfil.get("fuerza") or 2)
    nivel    = (perfil.get("nivel")   or "Intermedio").lower()
    objetivo = (perfil.get("objetivo") or "10K").lower()
    genero   = (perfil.get("genero")  or "Mujer").lower()

    # ── Señales de datos ──────────────────────────────────────────────────
    hrv         = datos.get("hrv_actual")
    hrv_tend    = datos.get("hrv_tendencia", 0.0) or 0.0
    dias_mal_s  = datos.get("dias_mal_sueno", 0) or 0
    fatiga      = int(datos.get("fatiga_reciente") or 5)
    ratio_carga = datos.get("ratio_ctl_atl")
    lesiones    = datos.get("lesiones_activas") or []
    estres      = int(datos.get("estres_vital") or 3)
    cadencia    = datos.get("cadencia_media")
    zancada     = datos.get("longitud_zancada_m")
    oscilacion  = datos.get("oscilacion_vertical")
    training_readiness = datos.get("training_readiness")
    body_battery = datos.get("body_battery")
    recovery_hours = datos.get("recovery_hours")
    sueño_profundo = datos.get("sleep_profundo_7d")
    despertares = datos.get("despertares_7d")
    fase_ciclo  = (datos.get("fase_ciclo_actual") or "").lower()
    rpe_ultimo  = datos.get("rpe_ultima")

    # ── Flags de alerta ───────────────────────────────────────────────────
    alertas = []
    intensidad_bloqueada = False
    reduccion_volumen = 1.0

    # HRV: indicador número uno de recuperación del SNC
    hrv_bajo    = hrv is not None and hrv < 50
    hrv_cayendo = hrv_tend < -5
    if hrv_bajo or hrv_cayendo:
        intensidad_bloqueada = True
        reduccion_volumen *= 0.75
        msg = f"HRV {'bajo (' + '%.0f ms' % hrv + ')' if hrv_bajo else 'cayendo (' + '%+.1f ms' % hrv_tend + ' tendencia)'}"
        alertas.append(f"⚠️ {msg}: sesiones de calidad canceladas → Z2 suave y recuperación activa.")

    # Sueño: 3+ días con score < 60 → reducción de volumen
    if dias_mal_s >= 3:
        intensidad_bloqueada = True
        reduccion_volumen *= 0.80
        alertas.append(f"😴 {dias_mal_s} días con sleep score < 60: volumen reducido y sin intensidad alta.")

    if training_readiness is not None and training_readiness < 40:
        intensidad_bloqueada = True
        reduccion_volumen *= 0.85
        alertas.append(f"🚦 Training Readiness {training_readiness}/100: hoy no toca calidad, solo rodaje regenerativo.")

    if body_battery is not None and body_battery < 35:
        intensidad_bloqueada = True
        reduccion_volumen *= 0.85
        alertas.append(f"🔋 Body Battery {body_battery}/100: energía baja. Se reduce la carga de la semana.")

    if recovery_hours is not None and recovery_hours >= 24:
        intensidad_bloqueada = True
        alertas.append(f"⏳ Garmin marca {recovery_hours:.0f} h de recuperación: se espacian las sesiones exigentes.")

    if sueño_profundo is not None and sueño_profundo < 1.2:
        reduccion_volumen *= 0.90
        alertas.append("🌙 Sueño profundo escaso en la última semana: baja capacidad de reparación muscular.")

    if despertares is not None and despertares >= 3:
        reduccion_volumen *= 0.95
        alertas.append(f"🌙 {despertares:.1f} despertares de media: posible fatiga del sistema nervioso.")

    # Carga aguda/crónica (ATL/CTL)
    if ratio_carga:
        if ratio_carga >= 1.5:
            intensidad_bloqueada = True
            reduccion_volumen *= 0.70
            alertas.append(f"🔴 Ratio carga aguda/crónica = {ratio_carga:.2f} → riesgo sobreentrenamiento. Semana de descarga forzada.")
        elif ratio_carga >= 1.3:
            intensidad_bloqueada = True
            alertas.append(f"🟡 Ratio carga = {ratio_carga:.2f}: sin series ni trabajo de alta intensidad esta semana.")

    # Estrés vital: el cuerpo no distingue estrés físico de mental
    if estres >= 7:
        reduccion_volumen *= 0.85
        dias_carrera = max(1, dias_carrera - 1)
        alertas.append(f"🧠 Estrés vital {estres}/10: una sesión de carrera reemplazada por movilidad activa.")

    # Fatiga subjetiva alta
    if fatiga >= 8:
        reduccion_volumen *= 0.80
        alertas.append(f"🫀 Fatiga subjetiva {fatiga}/10: volumen general reducido un 20%.")

    # RPE muy alto en última sesión
    if rpe_ultimo and rpe_ultimo >= 9:
        intensidad_bloqueada = True
        alertas.append(f"🎯 RPE última sesión = {rpe_ultimo}/10: recuperación prioritaria, sin intensidad.")

    # Ciclo menstrual femenino
    if genero == "mujer" and fase_ciclo:
        if "lútea" in fase_ciclo:
            reduccion_volumen *= 0.85
            alertas.append("🌕 Fase lútea: volumen reducido, sesiones en Z1-Z2. Evitar máxima intensidad.")
        elif "ovulat" in fase_ciclo:
            alertas.append("✨ Fase ovulatoria: ventana de alto rendimiento. Ideal para velocidad e intensidad.")
        elif "folicular" in fase_ciclo:
            alertas.append("🌱 Fase folicular: rendimiento en ascenso. Intensidad moderada-alta bien tolerada.")

    # Lesiones activas
    zonas_bajas = {"rodilla", "fascia", "gemelo", "tobillo", "plantar", "tibia"}
    sin_impacto  = any(any(z in l for z in zonas_bajas) for l in lesiones)
    sin_velocidad = any(any(z in l for z in {"isquio", "femoral", "hamstring"}) for l in lesiones)
    lumbar       = any(any(z in l for z in {"lumbar", "espalda"}) for l in lesiones)
    if sin_impacto:
        alertas.append(f"🩹 Lesión activa (zona de impacto): carrera sustituida por cardio sin impacto.")
    if sin_velocidad:
        alertas.append("🩹 Lesión activa en isquios: sin sprints ni series. Se añade excéntrico nórdico.")
    if lumbar:
        alertas.append("🩹 Zona lumbar/espalda: sin carga axial. Ejercicios de cadera y cadena posterior.")

    # Técnica de carrera (dinámica Garmin)
    necesita_drills = cadencia is not None and cadencia < 170
    necesita_core   = oscilacion is not None and oscilacion > 12.0
    if necesita_drills:
        alertas.append(f"👣 Cadencia {cadencia:.0f} spm (<170): se añaden drills de técnica en los rodajes.")
    if necesita_core:
        alertas.append(f"📐 Oscilación vertical {oscilacion:.1f} cm (>12): se añade trabajo de core y estabilidad.")
    if cadencia is not None and zancada is not None and cadencia < 170 and zancada > 1.15:
        alertas.append(f"🦵 Cadencia baja con zancada larga ({zancada:.2f} m): posible overstride. Se prioriza técnica para proteger rodilla.")

    # ── Parámetros base ───────────────────────────────────────────────────
    base_rodaje = {"principiante": 35, "intermedio": 45, "avanzado": 55, "élite": 70}.get(nivel, 45)
    km_tirada = {
        "5k / 10k":      "8-12 km",
        "media maratón": "14-18 km",
        "maratón":       "20-28 km",
        "trail":         "90-140 min en desnivel acumulado",
        "hyrox":         "60 min circuito mixto",
    }.get(objetivo, "10-14 km")

    rodaje_min = max(25, int(base_rodaje * reduccion_volumen))

    # ── Distribución de días ──────────────────────────────────────────────
    run_idx    = _indices_distribuidos(dias_carrera)
    fuerza_idx = [d for d in _indices_distribuidos(dias_fuerza + 1) if d not in run_idx][:dias_fuerza]

    # Regla premium: nunca fuerza pesada de piernas el día ANTES de series
    if run_idx and fuerza_idx:
        dia_series = min(run_idx)
        fuerza_idx = [
            (d + 1) % 7 if d == dia_series - 1 else d
            for d in fuerza_idx
        ]

    # ── Coordinación con pareja ───────────────────────────────────────────
    # Si hay plan de la pareja, intentamos mover días de entreno activo
    # para que coincidan con los días que ella/él también entrena.
    if plan_pareja is not None and not plan_pareja.empty:
        try:
            pareja_activa = plan_pareja[plan_pareja["tipo"].isin(["Carrera", "Fuerza", "Mixto", "Cardio alternativo"])]
            pareja_activa["i"] = pd.to_datetime(pareja_activa["fecha"]).apply(
                lambda d: (d.date() - fecha_inicio_semana.date()).days
            )
            dias_pareja = set(pareja_activa["i"].dropna().astype(int).tolist())
            if dias_pareja:
                dias_total_activos = set(run_idx) | set(fuerza_idx)
                # Calcular overlap actual y ideal
                overlap_actual = len(dias_total_activos & dias_pareja)
                # Intentar reasignar días de fuerza para mejorar overlap
                pool_candidatos = list(dias_pareja - set(run_idx))
                nuevos_fuerza = []
                for d in fuerza_idx:
                    if d not in dias_pareja and pool_candidatos:
                        candidato = pool_candidatos.pop(0)
                        if candidato not in run_idx and candidato not in nuevos_fuerza:
                            nuevos_fuerza.append(candidato)
                            continue
                    nuevos_fuerza.append(d)
                fuerza_idx = nuevos_fuerza
                coinciden = len((set(run_idx) | set(fuerza_idx)) & dias_pareja)
                if coinciden > overlap_actual:
                    alertas.append(
                        f"👫 Plan coordinado con tu pareja: {coinciden} días de entrenamiento coincidentes esta semana."
                    )
        except Exception:
            pass

    nombres = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    filas = []

    for i in range(7):
        fecha     = (fecha_inicio_semana + timedelta(days=i)).strftime("%Y-%m-%d")
        tipo      = "Recuperacion"
        sesion    = "Movilidad + respiración"
        detalles  = "20-30 min: foam roller, movilidad articular y respiración diafragmática."
        duracion  = 30
        intensidad = "Baja"

        # ── Días de carrera ───────────────────────────────────────────────
        if i in run_idx:
            if sin_impacto:
                tipo, sesion, intensidad, duracion = "Cardio alternativo", "Bicicleta / natación (sin impacto)", "Media", 50
                detalles = "45-55 min a ritmo aeróbico moderado. Mantiene carga cardiovascular sin agravar lesión."
            elif intensidad_bloqueada:
                tipo, sesion, intensidad, duracion = "Carrera", "Rodaje Z2 – recuperación activa", "Baja", rodaje_min
                detalles = ("Ritmo muy cómodo (Z1-Z2), conversación posible todo el tiempo. "
                            "Si en los primeros 10 min el cuerpo no responde bien, para.")
                if necesita_drills:
                    detalles += " Incluye 3 × 30 seg talón-glúteo y 3 × 20 m pies rápidos."
            else:
                if i == max(run_idx):           # Tirada larga
                    tipo, intensidad, duracion = "Carrera", "Media", rodaje_min + 25
                    if objetivo == "trail":
                        sesion   = "Tirada larga de montaña"
                        detalles = (f"Tiempo sobre las piernas: {km_tirada}. "
                                    "Practica ingesta de carbohidratos (60-90 g/h). "
                                    "Último tercio con trabajo excéntrico de bajada.")
                    elif objetivo in ("maratón", "media maratón"):
                        sesion   = "Tirada larga – umbral aeróbico"
                        detalles = (f"Ritmo Z2 sostenido. Objetivo: {km_tirada}. "
                                    "Métrica clave: misma FC = más km cada semana → estás mejorando.")
                    else:
                        sesion   = "Tirada larga"
                        detalles = f"Ritmo Z2 estable. Objetivo: {km_tirada}."
                elif i == min(run_idx):         # Sesión de calidad
                    tipo, duracion = "Carrera", rodaje_min
                    if sin_velocidad:
                        sesion, intensidad = "Progresivo aeróbico – sin velocidad", "Media"
                        detalles = ("Progresión suave dentro de Z2-Z3. Sin cambios bruscos. "
                                    "Post-carrera: 3 × 10 nórdico excéntrico isquio.")
                    elif objetivo in ("maratón", "media maratón"):
                        sesion, intensidad = "Tempo / umbral de lactato", "Alta"
                        detalles = ("10' calentar + 20-30 min al ritmo umbral (Z4) + 10' enfriar. "
                                    "Anota FC media del bloque para comparar semanas.")
                    elif objetivo == "hyrox":
                        sesion, intensidad = "Series HYROX", "Alta"
                        detalles = ("10' calentar + 5 × (400 m ritmo alto + 20 wall-balls / 250 m row) + 10' enfriar. "
                                    "Simula las estaciones de la prueba.")
                    else:
                        sesion, intensidad = "Series: calidad aeróbica", "Alta"
                        detalles = "10' calentar + 5 × (3 min Z4 / 2 min Z2) + 10' enfriar. Registra RPE real."
                else:                           # Rodaje intermedio
                    tipo, sesion, intensidad, duracion = "Carrera", "Rodaje aeróbico Z2", "Media", rodaje_min
                    detalles = "Ritmo conversacional Z2 constante, sin picos de FC."
                    if necesita_drills:
                        detalles += " Incluye 5 × 20 m drills: pies rápidos, rodillas altas, talón-glúteo."

        # ── Días de fuerza ────────────────────────────────────────────────
        if i in fuerza_idx:
            if tipo in ("Carrera", "Cardio alternativo"):
                tipo = "Mixto"
                if objetivo == "trail":
                    sesion   = f"{sesion} + Fuerza excéntrica"
                    detalles += (" 30 min post: step-down excéntrico, sentadilla búlgara, nórdicos. "
                                 "Clave para aguantar descensos largos sin destruir cuádriceps.")
                elif lumbar:
                    sesion   = f"{sesion} + Fuerza sin carga axial"
                    detalles += " 25 min: hip thrust, puente de glúteos, remo en máquina. Sin compresión lumbar."
                else:
                    sesion   = f"{sesion} + Fuerza funcional"
                    detalles += " 25-30 min: peso muerto rumano, sentadilla goblet, core antirotación."
                duracion += 30
                intensidad = "Media"
            else:
                tipo, duracion, intensidad = "Fuerza", 55, "Media"
                if objetivo == "hyrox":
                    sesion   = "Circuito de fuerza HYROX"
                    detalles = ("4 rondas: farmer carry 2×20 m, 15 wall-balls, 20 lunges con mancuerna, "
                                "250 m row, 10 burpees. Registra tiempo total. RPE objetivo: 7-8.")
                elif sin_velocidad:
                    sesion   = "Fuerza – excéntrico isquios"
                    detalles = ("Hip thrust 4×10, RDL 3×10 carga moderada, nórdico isquio 3×8 excéntrico controlado, "
                                "elevación de talón sentada 3×15. RPE máximo 7.")
                elif lumbar:
                    sesion   = "Fuerza – cadena posterior sin compresión"
                    detalles = "Hip thrust 4×10, remo horizontal 4×10, pull-down 3×12, core en suelo. RPE 7."
                else:
                    sesion   = "Fuerza estructural full-body"
                    detalles = ("Hip thrust 4×10, sentadilla búlgara 3×8, remo 4×10, "
                                "press hombro 3×10, plancha con rotación 3×30 seg. RPE 7-8.")

        # Core en días de descanso si oscilación vertical alta
        if tipo == "Recuperacion" and necesita_core:
            sesion  += " + Core estabilidad"
            detalles += " Añade 15 min: dead-bug 3×10, pallof press 3×12, RKC plancha 3×20 seg."

        filas.append({
            "dia": nombres[i], "fecha": fecha, "tipo": tipo,
            "sesion": sesion, "detalles": detalles,
            "duracion_min": duracion, "intensidad": intensidad,
        })

    return pd.DataFrame(filas), alertas


def guardar_plan_semanal(usuario_id, semana_inicio, plan_df):
    conn = get_db_connection()
    conn.execute(
        "DELETE FROM plan_entrenamiento WHERE usuario_id = ? AND semana_inicio = ?",
        (usuario_id, semana_inicio.strftime("%Y-%m-%d")),
    )
    for _, row in plan_df.iterrows():
        conn.execute(
            """
            INSERT INTO plan_entrenamiento
            (usuario_id, semana_inicio, fecha, tipo, sesion, detalles, duracion_min, intensidad, creado_en)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                usuario_id,
                semana_inicio.strftime("%Y-%m-%d"),
                row["fecha"],
                row["tipo"],
                row["sesion"],
                row["detalles"],
                int(row["duracion_min"]),
                row["intensidad"],
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
    conn.commit()
    conn.close()


def cargar_plan_semanal(usuario_id, semana_inicio):
    conn = get_db_connection()
    df = pd.read_sql_query(
        """
        SELECT fecha, tipo, sesion, detalles, duracion_min, intensidad
        FROM plan_entrenamiento
        WHERE usuario_id = ? AND semana_inicio = ?
        ORDER BY fecha
        """,
        conn,
        params=(usuario_id, semana_inicio.strftime("%Y-%m-%d")),
    )
    conn.close()
    return df


@st.cache_data(ttl=300)
def resumen_usuario_para_plan(usuario_id):
    conn = get_db_connection()
    out = {
        "carreras_14d": 0, "km_14d": 0.0, "fc_media_14d": None, "fuerza_14d": 0,
        "sueno_horas_7d": None, "sueno_score_7d": None, "dias_mal_sueno": 0,
        "sleep_profundo_7d": None, "sleep_rem_7d": None, "sleep_vigilia_7d": None, "despertares_7d": None,
        "fatiga_reciente": 5,
        "hrv_actual": None, "hrv_tendencia": 0.0,
        "fc_reposo": None, "fc_maxima": None,
        "carga_aguda": None, "carga_cronica": None, "ratio_ctl_atl": None,
        "cadencia_media": None, "longitud_zancada_m": None, "oscilacion_vertical": None, "tiempo_contacto": None,
        "potencia_media_w": None,
        "training_readiness": None, "body_battery": None, "recovery_hours": None, "spo2": None,
        "estres_vital": 3, "disponibilidad_min": 60,
        "rpe_ultima": None, "sensacion_ultima": "",
        "lesiones_activas": [],
        "fase_ciclo_actual": None,
    }
    try:
        fecha_14d = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%d")

        # ── Actividades running ──────────────────────────────────────────
        act = pd.read_sql_query(
            "SELECT distancia_m, fc_media FROM actividades_garmin WHERE usuario_id = ? AND fecha >= ?",
            conn, params=(usuario_id, fecha_14d),
        )
        if not act.empty:
            out["carreras_14d"] = len(act)
            out["km_14d"] = float(act["distancia_m"].fillna(0).sum() / 1000)
            out["fc_media_14d"] = float(act["fc_media"].dropna().mean()) if act["fc_media"].notna().any() else None

        # ── Fuerza ──────────────────────────────────────────────────────
        try:
            f = pd.read_sql_query(
                "SELECT COUNT(*) AS total FROM sesiones_fuerza WHERE usuario_id = ? AND fecha >= ?",
                conn, params=(usuario_id, fecha_14d),
            )
            out["fuerza_14d"] = int(f.iloc[0]["total"])
        except Exception:
            pass

        # ── Sueño ────────────────────────────────────────────────────────
        try:
            sueno = pd.read_sql_query(
                "SELECT horas_totales, score, sleep_profundo_horas, sleep_rem_horas, sleep_vigilia_horas, despertares FROM datos_sueno WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 7",
                conn, params=(usuario_id,),
            )
            if not sueno.empty:
                out["sueno_horas_7d"] = float(sueno["horas_totales"].fillna(0).mean())
                if "sleep_profundo_horas" in sueno.columns:
                    out["sleep_profundo_7d"] = float(sueno["sleep_profundo_horas"].fillna(0).mean())
                    out["sleep_rem_7d"] = float(sueno["sleep_rem_horas"].fillna(0).mean())
                    out["sleep_vigilia_7d"] = float(sueno["sleep_vigilia_horas"].fillna(0).mean())
                if "despertares" in sueno.columns:
                    desper = sueno["despertares"].dropna()
                    if not desper.empty:
                        out["despertares_7d"] = float(desper.mean())
                if "score" in sueno.columns:
                    scores = sueno["score"].dropna()
                    if not scores.empty:
                        out["sueno_score_7d"] = float(scores.mean())
                        out["dias_mal_sueno"] = int((scores < 60).sum())
        except Exception:
            pass

        # ── Fatiga subjetiva y fase del ciclo ────────────────────────────
        try:
            fisio = pd.read_sql_query(
                "SELECT fatiga_subjetiva, fase_ciclo FROM diario_fisiologia WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 3",
                conn, params=(usuario_id,),
            )
            if not fisio.empty:
                f0 = fisio.iloc[0]
                if pd.notna(f0.get("fatiga_subjetiva")):
                    out["fatiga_reciente"] = int(f0["fatiga_subjetiva"])
                if pd.notna(f0.get("fase_ciclo")) and f0["fase_ciclo"] != "No Aplica":
                    out["fase_ciclo_actual"] = f0["fase_ciclo"]
        except Exception:
            pass

        # ── Biométricos premium ──────────────────────────────────────────
        try:
            prem = pd.read_sql_query(
                """
                SELECT fecha, hrv_ms, fc_reposo, fc_maxima, carga_aguda, carga_cronica,
                      cadencia_media, longitud_zancada_m, oscilacion_vertical_cm, tiempo_contacto_ms,
                      estres_vital, disponibilidad_min, rpe_sesion, sensacion_notas, sleep_score,
                      training_readiness, body_battery, recovery_hours, spo2, potencia_media_w
                FROM datos_biometricos_premium
                WHERE usuario_id = ?
                ORDER BY fecha DESC
                LIMIT 14
                """,
                conn, params=(usuario_id,),
            )
            if not prem.empty:
                p0 = prem.iloc[0]
                def _f(col): return float(p0[col]) if pd.notna(p0.get(col)) else None
                def _i(col): return int(p0[col]) if pd.notna(p0.get(col)) else None
                out["hrv_actual"]        = _f("hrv_ms")
                out["fc_reposo"]         = _i("fc_reposo")
                out["fc_maxima"]         = _i("fc_maxima")
                out["carga_aguda"]       = _f("carga_aguda")
                out["carga_cronica"]     = _f("carga_cronica")
                out["cadencia_media"]    = _f("cadencia_media")
                out["longitud_zancada_m"] = _f("longitud_zancada_m")
                out["oscilacion_vertical"] = _f("oscilacion_vertical_cm")
                out["tiempo_contacto"]   = _f("tiempo_contacto_ms")
                out["potencia_media_w"]  = _f("potencia_media_w")
                out["estres_vital"]      = _i("estres_vital") or 3
                out["disponibilidad_min"] = _i("disponibilidad_min") or 60
                out["rpe_ultima"]        = _i("rpe_sesion")
                out["training_readiness"] = _i("training_readiness")
                out["body_battery"]      = _i("body_battery")
                out["recovery_hours"]    = _f("recovery_hours")
                out["spo2"]              = _f("spo2")
                out["sensacion_ultima"]  = str(p0["sensacion_notas"]) if pd.notna(p0.get("sensacion_notas")) else ""
                # Sleep score desde premium si datos_sueno no lo tiene
                if out["sueno_score_7d"] is None:
                    sc = prem["sleep_score"].dropna()
                    if not sc.empty:
                        out["sueno_score_7d"] = float(sc.mean())
                        out["dias_mal_sueno"] = int((sc < 60).sum())
                # Tendencia HRV: media últimos 7 vs anteriores
                hrv_s = prem["hrv_ms"].dropna()
                if len(hrv_s) >= 4:
                    mid = len(hrv_s) // 2
                    out["hrv_tendencia"] = float(hrv_s.iloc[:mid].mean() - hrv_s.iloc[mid:].mean())
                # Ratio carga
                if out["carga_aguda"] and out["carga_cronica"] and out["carga_cronica"] > 0:
                    out["ratio_ctl_atl"] = round(out["carga_aguda"] / out["carga_cronica"], 2)
        except Exception:
            pass

        # ── Lesiones activas ─────────────────────────────────────────────
        try:
            les = pd.read_sql_query(
                "SELECT zona FROM historial_lesiones WHERE usuario_id = ? AND activa = 1",
                conn, params=(usuario_id,),
            )
            if not les.empty:
                out["lesiones_activas"] = les["zona"].str.lower().tolist()
        except Exception:
            pass

    finally:
        conn.close()

    return out


def inicio_semana(fecha_obj):
    return fecha_obj - timedelta(days=fecha_obj.weekday())


@st.cache_data(ttl=60)
def resumen_dashboard(usuario_id):
    conn = get_db_connection()
    out = {
        "km_7d": 0.0,
        "runs_7d": 0,
        "fuerza_7d": 0,
        "sueno_7d": None,
        "fatiga": None,
    }
    try:
        f7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        act = pd.read_sql_query(
            "SELECT distancia_m FROM actividades_garmin WHERE usuario_id = ? AND fecha >= ?",
            conn,
            params=(usuario_id, f7),
        )
        if not act.empty:
            out["runs_7d"] = len(act)
            out["km_7d"] = float(act["distancia_m"].fillna(0).sum() / 1000)

        try:
            fuerza = pd.read_sql_query(
                "SELECT COUNT(*) AS total FROM sesiones_fuerza WHERE usuario_id = ? AND fecha >= ?",
                conn,
                params=(usuario_id, f7),
            )
            out["fuerza_7d"] = int(fuerza.iloc[0]["total"])
        except Exception:
            try:
                fuerza = pd.read_sql_query(
                    "SELECT COUNT(*) AS total FROM entrenamientos_fuerza WHERE fecha >= ?",
                    conn,
                    params=(f7,),
                )
                out["fuerza_7d"] = int(fuerza.iloc[0]["total"])
            except Exception:
                pass

        try:
            sueno = pd.read_sql_query(
                "SELECT horas_totales FROM datos_sueno WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 7",
                conn,
                params=(usuario_id,),
            )
            if not sueno.empty:
                out["sueno_7d"] = float(sueno["horas_totales"].fillna(0).mean())
        except Exception:
            pass

        fisio = pd.read_sql_query(
            "SELECT fatiga_subjetiva FROM diario_fisiologia WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 1",
            conn,
            params=(usuario_id,),
        )
        if not fisio.empty:
            out["fatiga"] = int(fisio.iloc[0]["fatiga_subjetiva"])
    finally:
        conn.close()
    return out


def construir_calendario_semanal_actividades(df_act, df_fuerza, semana_inicio):
    semana_fin = semana_inicio + timedelta(days=6)
    out = pd.DataFrame(
        {
            "fecha": pd.date_range(start=semana_inicio, end=semana_fin, freq="D"),
        }
    )
    out["dia"] = out["fecha"].dt.day_name().map(
        {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miercoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sabado",
            "Sunday": "Domingo",
        }
    )
    out["run_desc"] = ""
    out["gym_desc"] = ""

    if not df_act.empty:
        act = df_act.copy()
        act["fecha_dt"] = pd.to_datetime(act["fecha"]).dt.tz_localize(None).dt.date
        act["km"] = act["distancia_m"].fillna(0) / 1000
        semana_act = act[(act["fecha_dt"] >= semana_inicio.date()) & (act["fecha_dt"] <= semana_fin.date())]
        if not semana_act.empty:
            agg = semana_act.groupby("fecha_dt", as_index=False).agg(km=("km", "sum"), total=("km", "size"))
            for _, r in agg.iterrows():
                idx = out[out["fecha"].dt.date == r["fecha_dt"]].index
                if len(idx):
                    out.loc[idx[0], "run_desc"] = f"{r['total']} run · {r['km']:.1f} km"

    if not df_fuerza.empty:
        fuer = df_fuerza.copy()
        fuer["fecha_dt"] = pd.to_datetime(fuer["fecha"]).dt.date
        semana_f = fuer[(fuer["fecha_dt"] >= semana_inicio.date()) & (fuer["fecha_dt"] <= semana_fin.date())]
        if not semana_f.empty:
            agg_f = semana_f.groupby("fecha_dt", as_index=False).agg(total=("fecha", "size"))
            for _, r in agg_f.iterrows():
                idx = out[out["fecha"].dt.date == r["fecha_dt"]].index
                if len(idx):
                    out.loc[idx[0], "gym_desc"] = f"{r['total']} sesion fuerza"

    out["actividad"] = out.apply(
        lambda r: " | ".join([x for x in [r["run_desc"], r["gym_desc"]] if x]) if (r["run_desc"] or r["gym_desc"]) else "Descanso / movilidad",
        axis=1,
    )
    return out


def progreso_running(df_act):
    if df_act.empty:
        return pd.DataFrame()
    run = df_act.copy()
    run["fecha_dt"] = pd.to_datetime(run["fecha"]).dt.tz_localize(None)
    run["km"] = run["distancia_m"].fillna(0) / 1000
    run = run.sort_values("fecha_dt")
    run["week"] = run["fecha_dt"].dt.to_period("W-MON").dt.start_time
    out = run.groupby("week", as_index=False).agg(km_semana=("km", "sum"), fc_media=("fc_media", "mean"), sesiones=("km", "size"))
    return out


def _mapear_grupos_musculares(texto):
    if not isinstance(texto, str):
        texto = ""
    t = texto.lower()
    grupos = {
        "gluteos": ["glute", "gluteo", "glúteo"],
        "espalda biceps": ["espalda", "dorsal", "remo", "dominada", "bicep", "bícep"],
        "isquios": ["isquio", "femoral", "hamstring"],
        "cuadriceps": ["cuadrice", "cuádrice", "quad"],
        "gemelos": ["gemelo", "pantorrilla", "soleo", "sóleo"],
        "triceps": ["tricep", "trícep", "extension codo"],
        "hombro": ["hombro", "delto"],
        "abdominales": ["abdominal", "core", "abs"],
    }
    encontrados = [g for g, keys in grupos.items() if any(k in t for k in keys)]
    return encontrados if encontrados else ["abdominales"]


def progreso_fuerza_grupos(df_fuerza):
    if df_fuerza.empty:
        return pd.DataFrame()
    df = df_fuerza.copy()
    df["fecha_dt"] = pd.to_datetime(df["fecha"]).dt.tz_localize(None)
    df["peso"] = pd.to_numeric(df.get("peso", 0), errors="coerce").fillna(0)
    df["series"] = pd.to_numeric(df.get("series", 0), errors="coerce").fillna(0)
    df["repeticiones"] = pd.to_numeric(df.get("repeticiones", 0), errors="coerce").fillna(0)
    df["volumen"] = (df["peso"] * df["series"] * df["repeticiones"]).clip(lower=0)
    df.loc[df["volumen"] == 0, "volumen"] = (df["series"] * df["repeticiones"]).clip(lower=0)

    filas = []
    for _, row in df.iterrows():
        grupos = _mapear_grupos_musculares(row.get("musculo_principal", ""))
        for g in grupos:
            filas.append({"fecha_dt": row["fecha_dt"], "grupo": g, "volumen": row["volumen"]})

    if not filas:
        return pd.DataFrame()

    out = pd.DataFrame(filas)
    out = out.groupby(["fecha_dt", "grupo"], as_index=False).agg(volumen=("volumen", "sum"))
    return out.sort_values("fecha_dt")


def predecir_fases_ciclo(df_fisio, horizonte_dias=90):
    if df_fisio.empty:
        return pd.DataFrame(columns=["fecha", "fase_ciclo", "origen"]), 28

    real = df_fisio.copy()
    real["fecha_dt"] = pd.to_datetime(real["fecha"]).dt.date
    real = real.sort_values("fecha_dt")

    starts = real[real["fase_ciclo"] == "Fase Folicular"]["fecha_dt"].drop_duplicates().tolist()
    ciclo_dias = 28
    if len(starts) >= 2:
        diffs = [(starts[i] - starts[i - 1]).days for i in range(1, len(starts))]
        diffs = [d for d in diffs if 20 <= d <= 40]
        if diffs:
            ciclo_dias = int(round(sum(diffs) / len(diffs)))

    base = starts[-1] if starts else real["fecha_dt"].max()
    pred = []
    for day in range(1, horizonte_dias + 1):
        fecha = base + timedelta(days=day)
        pos = day % ciclo_dias
        if pos <= 12:
            fase = "Fase Folicular"
        elif pos <= 15:
            fase = "Fase Ovulatoria"
        else:
            fase = "Fase Lútea"
        pred.append({"fecha": fecha, "fase_ciclo": fase, "origen": "Predicho"})

    pred_df = pd.DataFrame(pred)
    real_df = real[["fecha_dt", "fase_ciclo"]].rename(columns={"fecha_dt": "fecha"})
    real_df["origen"] = "Registrado"

    combinado = pd.concat([pred_df, real_df], ignore_index=True)
    combinado = combinado.sort_values(["fecha", "origen"]).drop_duplicates(subset=["fecha"], keep="last")
    return combinado, ciclo_dias


def render_calendario_ciclo(df_ciclo, anio, mes):
    mes_matrix = calendar.monthcalendar(anio, mes)
    fases = {}
    origen = {}
    for _, row in df_ciclo.iterrows():
        if isinstance(row["fecha"], pd.Timestamp):
            d = row["fecha"].date()
        else:
            d = row["fecha"]
        if d.month == mes and d.year == anio:
            fases[d.day] = row["fase_ciclo"]
            origen[d.day] = row["origen"]

    colores = {
        "Fase Folicular": "#fda4af",
        "Fase Ovulatoria": "#86efac",
        "Fase Lútea": "#93c5fd",
    }

    st.markdown("**Calendario del ciclo**")
    dias_header = ["L", "M", "X", "J", "V", "S", "D"]
    cols_h = st.columns(7)
    for i, d in enumerate(dias_header):
        cols_h[i].markdown(f"**{d}**")

    for semana in mes_matrix:
        cols = st.columns(7)
        for i, day in enumerate(semana):
            with cols[i]:
                if day == 0:
                    st.markdown(" ")
                    continue
                fase = fases.get(day)
                org = origen.get(day, "")
                bg = colores.get(fase, "#f8fafc")
                lbl = fase.replace("Fase ", "") if isinstance(fase, str) else "-"
                borde = "2px solid #0f172a" if org == "Registrado" else "1px dashed #334155"
                st.markdown(
                    f"""
                    <div style='background:{bg}; border:{borde}; border-radius:8px; padding:8px; min-height:66px;'>
                        <div style='font-weight:700; color:#0f172a;'>{day}</div>
                        <div style='font-size:0.75rem; color:#1e293b;'>{lbl}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# 1. CONFIGURACIÓN DE PÁGINA
st.set_page_config(page_title="Proyecto Athlete", page_icon="🏃‍♀️", layout="wide")
asegurar_tabla_plan_entrenamiento()
asegurar_tablas_fuerza()
asegurar_tablas_premium()

# Ocultar sidebar completa
st.markdown(
    """<style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="collapsedControl"] { display: none; }
    </style>""",
    unsafe_allow_html=True,
)

# 2. LÓGICA DE LOGIN / SESIÓN
if "usuario_id" not in st.session_state:
    # Intentar cargar el último usuario recordado en este dispositivo
    ultimo = _leer_ultimo_usuario()
    if ultimo:
        st.session_state.usuario_id = ultimo
        st.rerun()

    st.markdown(
        """
        <style>
        .login-wrap { max-width:420px; margin:72px auto 32px; text-align:center; }
        .login-badge {
            width:62px; height:62px;
            background:linear-gradient(135deg,#6b8f12 0%,#d9f20f 100%);
            border-radius:18px; margin:0 auto 18px;
            display:flex; align-items:center; justify-content:center;
            box-shadow:0 8px 24px rgba(107,143,18,0.30);
        }
        .login-badge svg { width:30px; height:30px; fill:white; }
        .login-title { font-size:1.75rem; font-weight:800; color:#123126; margin:0 0 6px; letter-spacing:-0.03em; }
        .login-sub { color:#315447; font-size:0.95rem; margin:0 0 28px; }
        </style>
        <div class="login-wrap">
            <div class="login-badge">
                <svg viewBox="0 0 24 24"><path d="M13.49 5.48c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm-3.6 13.9l1-4.4 2.1 2v6h2v-7.5l-2.1-2 .6-3c1.3 1.5 3.3 2.5 5.5 2.5v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1l-5.2 2.2v4.7h2v-3.4l1.8-.7-1.6 8.1-4.9-1-.4 2 7 1.4z"/></svg>
            </div>
            <div class="login-title">Proyecto Athlete</div>
            <div class="login-sub">Selecciona tu perfil de atleta</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("Malena", use_container_width=True, type="primary"):
            st.session_state.usuario_id = 1
            _guardar_ultimo_usuario(1)
            st.rerun()
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        if st.button("Dani", use_container_width=True):
            st.session_state.usuario_id = 2
            _guardar_ultimo_usuario(2)
            st.rerun()
    st.stop()

user_actual = st.session_state.usuario_id
perfil = obtener_perfil(user_actual)

# 3. ONBOARDING (Configuración inicial de Perfil + Garmin)
if perfil is None:
    st.title("Proyecto Athlete")
    st.subheader("Configura tu perfil de atleta y conexión Garmin")
    
    with st.form("onboarding_form"):
        col1, col2 = st.columns(2)
        with col1:
            nombre = st.text_input("Tu Nombre", placeholder="Ej: Malena")
            edad = st.number_input("Edad", 18, 99, 25)
            genero = st.selectbox("Fisiología", ["Mujer", "Hombre"])
            peso = st.number_input("Peso actual (kg)", 40.0, 150.0, 60.0)
            categoria = st.selectbox("Tipo de Evento", ["5K / 10K", "Media Maratón", "Maratón", "Trail", "HYROX"])
            
            st.divider()
            st.markdown("**🔐 Conexión Garmin Connect**")
            email_garmin = st.text_input("Email Garmin")
            pass_garmin = st.text_input("Contraseña Garmin", type="password")
        
        with col2:
            st.markdown("**⚡ Rendimiento y Disponibilidad**")
            def format_ritmo(seg): return f"{seg // 60}:{seg % 60:02d}"
            seg_inf = st.select_slider("Límite superior (Rápido)", options=range(150, 485, 5), value=240, format_func=format_ritmo)
            seg_sup = st.select_slider("Límite inferior (Lento)", options=range(150, 485, 5), value=250, format_func=format_ritmo)
            
            st.divider()
            carrera = st.slider("Días de carrera/semana", 1, 7, 4)
            fuerza = st.slider("Días de fuerza/semana", 0, 7, 2)
            nivel = st.select_slider("Nivel actual", ["Principiante", "Intermedio", "Avanzado", "Élite"])
            
        if st.form_submit_button("🚀 Generar mi Ecosistema"):
            datos = {
                "nombre": nombre, "edad": edad, "genero": genero, "peso": peso,
                "objetivo": categoria, "carrera": carrera, "fuerza": fuerza,
                "nivel": nivel, "ritmo": f"{format_ritmo(seg_inf)}-{format_ritmo(seg_sup)}"
            }
            guardar_perfil(user_actual, datos)
            
            if email_garmin and pass_garmin:
                pass_enc = encriptar_password(pass_garmin)
                conn = get_db_connection()
                conn.execute("UPDATE usuarios SET email_garmin = ?, password_garmin_enc = ? WHERE id = ?", (email_garmin, pass_enc, user_actual))
                conn.commit()
                conn.close()
            st.rerun()
    st.stop()

# 4. MENÚ SUPERIOR CON SELECTOR DE PERFIL
nombre_usuario = perfil.get("nombre", "Atleta") if perfil else "Atleta"
_bienvenida = f"Bienvenida, {nombre_usuario}" if user_actual == 1 else f"Bienvenido, {nombre_usuario}"

st.markdown(
    f"""
    <style>
    :root {
        --ath-bg: #ecf2e3;
        --ath-surface: #f3f7eb;
        --ath-card: #eef4df;
        --ath-border: #c5d1b0;
        --ath-text: #123126;
        --ath-text-soft: #315447;
        --ath-brand-deep: #082d27;
        --ath-brand-mid: #12443a;
        --ath-lime: #d9f20f;
        --ath-olive: #6b8f12;
    }
    /* ─── Global typography ─── */
    html, body, [class*="css"] {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Inter', Roboto, sans-serif;
    }}
    [data-testid="stAppViewContainer"] {{
        background:
            radial-gradient(circle at 8% 8%, rgba(217,242,15,0.10) 0%, transparent 38%),
            linear-gradient(180deg, var(--ath-bg) 0%, #e8efdc 100%);
        color: var(--ath-text);
    }}
    [data-testid="stHeader"] {{
        background: rgba(236,242,227,0.75);
        backdrop-filter: blur(8px);
    }}
    /* ─── Header brand bar ─── */
    .nav-outer {{
        background:
            radial-gradient(ellipse at 8% 50%, rgba(217,242,15,0.19) 0%, transparent 55%),
            linear-gradient(135deg, var(--ath-brand-deep) 0%, var(--ath-brand-mid) 48%, var(--ath-brand-deep) 100%);
        border-radius: 20px;
        padding: 14px 20px 12px 20px;
        margin-bottom: 16px;
        box-shadow: 0 12px 40px rgba(2,6,23,0.28);
        border: 1px solid rgba(217,242,15,0.22);
    }}
    .athlete-brand {{
        display: flex;
        align-items: center;
        gap: 13px;
        padding: 2px 0 4px 0;
    }}
    .brand-icon {{
        width: 44px; height: 44px;
        background: linear-gradient(135deg, var(--ath-olive) 0%, var(--ath-lime) 100%);
        border-radius: 12px;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
        box-shadow: 0 4px 14px rgba(107,143,18,0.38);
    }}
    .brand-icon svg {{ width:24px; height:24px; fill:white; }}
    .brand-text-title {{
        font-size: 1.22rem; font-weight: 800; color: #f0fdfa;
        letter-spacing: -0.022em; line-height: 1.2;
    }}
    .brand-text-sub {{
        font-size: 0.79rem; color: rgba(204,251,241,0.78);
        font-weight: 400; line-height: 1.1; margin-top: 2px;
    }}
    /* ─── Nav radio ─── */
    div[data-testid="stHorizontalBlock"] [role="radiogroup"] {{
        gap: 0.45rem;
        background: rgba(248, 255, 234, 0.10);
        border: 1px solid rgba(217,242,15,0.22);
        padding: 0.38rem;
        border-radius: 13px;
        backdrop-filter: blur(8px);
    }}
    div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"] {{
        min-height: 42px;
        background: rgba(241, 247, 229, 0.95);
        border: 1px solid rgba(145, 163, 111, 0.36);
        border-radius: 9px;
        padding: 6px 13px;
        display: flex; align-items: center; justify-content: center;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.42);
        transition: all 0.16s ease;
    }}
    div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"] > div {{
        color: var(--ath-text) !important;
        font-weight: 600;
        opacity: 1 !important;
        font-size: 0.865rem;
        letter-spacing: 0.008em;
    }}
    div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"] svg {{
        fill: var(--ath-text) !important;
    }}
    div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"]:hover {{
        transform: translateY(-1px);
        border-color: rgba(217,242,15,0.65);
        background: #f7fbef;
    }}
    div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"][aria-checked="true"] {{
        background: linear-gradient(160deg, #f8fce9 0%, #eef7d7 100%);
        border-color: var(--ath-olive);
        box-shadow: 0 5px 16px rgba(107,143,18,0.25);
    }}
    div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"][aria-checked="true"] > div {{
        color: #365513 !important;
        font-weight: 700;
    }}
    /* ─── Profile selectbox ─── */
    div[data-testid="stSelectbox"] > div[data-baseweb="select"] {{
        background: rgba(240,246,227,0.95);
        border-radius: 10px;
        border: 1px solid rgba(145,163,111,0.38);
        min-height: 42px;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.48);
    }}
    div[data-testid="stSelectbox"] svg {{ fill: var(--ath-text); }}
    /* ─── Metric cards ─── */
    [data-testid="stMetric"] {{
        background: var(--ath-card);
        border: 1px solid var(--ath-border);
        border-radius: 14px;
        padding: 16px 18px;
        box-shadow: 0 1px 5px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s ease;
    }}
    [data-testid="stMetric"]:hover {{
        box-shadow: 0 5px 18px rgba(0,0,0,0.09);
    }}
    [data-testid="stMetricLabel"] p {{
        font-size: 0.72rem !important;
        color: var(--ath-text-soft) !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.065em !important;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 1.52rem !important;
        font-weight: 800 !important;
        color: var(--ath-text) !important;
        letter-spacing: -0.02em !important;
    }}
    /* ─── Primary buttons ─── */
    .stButton > button {{
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        letter-spacing: 0.008em !important;
        transition: all 0.18s ease !important;
    }}
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #55760f 0%, #d9f20f 100%) !important;
        color: #0f291f !important;
        border: none !important;
        box-shadow: 0 3px 10px rgba(107,143,18,0.28) !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 20px rgba(107,143,18,0.38) !important;
    }}
    .stButton > button:not([kind="primary"]) {{
        background: #edf4dd !important;
        color: var(--ath-text) !important;
        border: 1px solid #b7c99a !important;
    }}
    .stButton > button:not([kind="primary"]):hover {{
        background: #e3efcc !important;
        border-color: #8aa863 !important;
        transform: translateY(-1px) !important;
    }}
    /* ─── Garmin sync pill button ─── */
    .garmin-btn button {{
        background: linear-gradient(135deg, #0c3c31 0%, #254f0a 100%) !important;
        color: #f0fdfa !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.82rem !important;
        letter-spacing: 0.015em !important;
        box-shadow: 0 3px 12px rgba(12,60,49,0.36) !important;
        transition: all 0.2s ease !important;
        min-height: 42px !important;
        width: 100% !important;
    }}
    .garmin-btn button:hover {{
        box-shadow: 0 6px 20px rgba(12,60,49,0.45) !important;
        transform: translateY(-1px) !important;
    }}
    /* ─── Expanders ─── */
    details[data-testid="stExpander"] {{
        border: 1px solid var(--ath-border) !important;
        border-radius: 12px !important;
        overflow: hidden;
        background: var(--ath-surface);
    }}
    details[data-testid="stExpander"] summary {{
        padding: 12px 16px !important;
        font-weight: 600 !important;
        color: var(--ath-text) !important;
        background: #e9f2d6 !important;
    }}
    /* ─── Dividers ─── */
    hr {{
        border: none !important;
        border-top: 1px solid #cdd9b9 !important;
        margin: 18px 0 !important;
    }}
    /* ─── Responsive ─── */
    @media (max-width: 900px) {{
        .nav-outer {{ padding: 10px 12px 8px 12px; border-radius: 14px; }}
        .brand-text-title {{ font-size: 1.05rem; }}
        div[data-testid="stHorizontalBlock"] [role="radiogroup"] {{
            gap: 0.28rem; padding: 0.28rem;
        }}
        div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"] {{
            min-height: 36px; padding: 4px 8px;
        }}
        div[data-testid="stHorizontalBlock"] label[data-baseweb="radio"] > div {{
            font-size: 0.76rem;
        }}
        [data-testid="stMetricValue"] {{ font-size: 1.25rem !important; }}
        [data-testid="stMetricLabel"] p {{ font-size: 0.62rem !important; }}
    }}
    @media (max-width: 600px) {{
        .brand-icon {{ width:36px; height:36px; border-radius:9px; }}
        .brand-text-title {{ font-size: 0.95rem; }}
        .brand-text-sub {{ font-size: 0.70rem; }}
    }}
    </style>
    <div class="nav-outer">
        <div class="athlete-brand">
            <div class="brand-icon">
                <svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path d="M13.49 5.48c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm-3.6 13.9l1-4.4 2.1 2v6h2v-7.5l-2.1-2 .6-3c1.3 1.5 3.3 2.5 5.5 2.5v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1l-5.2 2.2v4.7h2v-3.4l1.8-.7-1.6 8.1-4.9-1-.4 2 7 1.4z"/>
                </svg>
            </div>
            <div>
                <div class="brand-text-title">Proyecto Athlete</div>
                <div class="brand-text-sub">{_bienvenida}</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Opciones de menú según perfil ─────────────────────────────────────────
_opciones_menu = [
    "Dashboard",
    "Biblioteca Científica",
    "Asistente Virtual",
    "Diario de Fuerza",
    "Entrenador Personal",
    "Calendario",
]
if user_actual == 1:  # Ciclo Menstrual solo para Malena
    _opciones_menu.insert(2, "Ciclo Menstrual")

# ── Fila nav: radio + botón Garmin + selector de perfil ───────────────────
_perfiles = {"Malena": 1, "Dani": 2}
_perfil_actual_nombre = "Malena" if user_actual == 1 else "Dani"
_nav_col, _garmin_col, _sel_col = st.columns([0.63, 0.20, 0.17])

with _garmin_col:
    st.markdown('<div class="garmin-btn">', unsafe_allow_html=True)
    _do_sync = st.button("↺  Sincronizar Garmin", key="garmin_sync_header", use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

with _sel_col:
    _elegido = st.selectbox(
        "Perfil",
        list(_perfiles.keys()),
        index=list(_perfiles.keys()).index(_perfil_actual_nombre),
        label_visibility="collapsed",
    )
    if _perfiles[_elegido] != user_actual:
        st.session_state.usuario_id = _perfiles[_elegido]
        _guardar_ultimo_usuario(_perfiles[_elegido])
        st.rerun()

with _nav_col:
    menu = st.radio(
        "Navegación principal",
        _opciones_menu,
        horizontal=True,
        label_visibility="collapsed",
    )

# ── Lógica de sincronización Garmin ───────────────────────────────────────
if _do_sync:
    cred = obtener_credenciales_garmin(user_actual)
    if cred and cred[0]:
        with st.spinner("Conectando con Garmin…"):
            try:
                email_g, p_enc_g = cred
                pw_g = desencriptar_password(p_enc_g)
                n_carreras = sincronizar_actividades_inteligente(email_g, pw_g, user_actual)
                n_bio = sincronizar_biometricos_garmin(email_g, pw_g, user_actual, dias=7)
                client_g = iniciar_sesion_garmin(email_g, pw_g)
                hoy_g = datetime.now()
                for _i in range(3):
                    _fd = hoy_g - timedelta(days=_i)
                    _ds = obtener_datos_sueno(client_g, _fd)
                    if _ds:
                        guardar_sueno_db(user_actual, _ds)
                st.cache_data.clear()
                st.toast(f"Sincronizado — {n_carreras} actividades · {n_bio} días biométricos")
                st.rerun()
            except Exception as _e:
                st.error(f"Error al sincronizar: {_e}")
    else:
        st.warning("Configura tus credenciales Garmin en el perfil.")

# ==========================================
# PESTAÑA 1: DASHBOARD (Con lógica de Sueño unificada)
# ==========================================
if menu == "Dashboard":
    st.markdown(
        "<h2 style='font-size:1.5rem;font-weight:800;color:#0f172a;letter-spacing:-0.02em;margin-bottom:4px;'>Dashboard</h2>",
        unsafe_allow_html=True,
    )

    conn = get_db_connection()
    # Leemos datos filtrados por usuario
    df_act = pd.read_sql_query(f"SELECT * FROM actividades_garmin WHERE usuario_id = {user_actual}", conn)
    try:
        df_sueno = pd.read_sql_query(
            f"SELECT * FROM datos_sueno WHERE usuario_id = {user_actual} ORDER BY fecha DESC LIMIT 7",
            conn,
        )
    except Exception:
        df_sueno = pd.DataFrame()

    try:
        df_fuerza = pd.read_sql_query(
            """
            SELECT s.fecha, e.peso, e.series, e.repeticiones, e.musculo_principal
            FROM ejercicios_fuerza e
            INNER JOIN sesiones_fuerza s ON s.id = e.sesion_id
            WHERE s.usuario_id = ?
            ORDER BY s.fecha
            """,
            conn,
            params=(user_actual,),
        )
    except Exception:
        try:
            df_fuerza = pd.read_sql_query(
                "SELECT fecha, peso, series, repeticiones, musculo_principal FROM entrenamientos_fuerza",
                conn,
            )
        except Exception:
            df_fuerza = pd.DataFrame()

    conn.close()

    # Resumen rápido de lo importante
    resumen = resumen_dashboard(user_actual)
    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Km (7d)", f"{resumen['km_7d']:.1f}")
    r2.metric("Carreras (7d)", resumen["runs_7d"])
    r3.metric("Fuerza (7d)", resumen["fuerza_7d"])
    r4.metric("Sueño medio (7d)", "-" if resumen["sueno_7d"] is None else f"{resumen['sueno_7d']:.1f} h")

    if user_actual == 2:
        estado_malena = obtener_estado_ciclo_malena()
        if estado_malena:
            st.divider()
            st.subheader("🩷 Estado del ciclo de Malena")
            c1, c2 = st.columns([0.35, 0.65])
            with c1:
                st.metric("Fase actual", estado_malena["fase"].replace("Fase ", ""))
                if estado_malena["proxima_regla"]:
                    faltan = (estado_malena["proxima_regla"] - datetime.now().date()).days
                    st.metric("Próxima regla", f"{faltan} días" if faltan >= 0 else "Hoy")
            with c2:
                st.caption(f"Origen del dato: {estado_malena['origen']}")
                for consejo in estado_malena["consejos"]:
                    st.info(consejo)

    st.divider()
    st.subheader("🏁 Checkpoints y pequeños logros")
    df_check = construir_checkpoints_objetivo(perfil, df_act)
    if not df_check.empty:
        completados = int((df_check["estado"] == "✅ Hecho").sum())
        progreso = completados / len(df_check)
        st.progress(progreso)
        st.caption(f"{completados} de {len(df_check)} checkpoints completados para el objetivo {perfil.get('objetivo', 'actual')}.")
        st.dataframe(df_check, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("🗓️ Calendario semanal de actividades")
    semana = inicio_semana(datetime.now())
    cal_semana = construir_calendario_semanal_actividades(df_act, df_fuerza, semana)
    cols_sem = st.columns(7)
    for i, row in cal_semana.iterrows():
        with cols_sem[i]:
            st.markdown(
                f"""
                <div style='background:#f8fafc;border:1px solid #cbd5e1;border-radius:10px;padding:10px;min-height:110px;'>
                    <div style='font-weight:700;color:#0f172a;'>{row['dia']}</div>
                    <div style='font-size:0.78rem;color:#475569;margin-bottom:6px;'>{row['fecha'].strftime('%d/%m')}</div>
                    <div style='font-size:0.84rem;color:#1e293b;'>{row['actividad']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()
    st.subheader("🏃 Progreso de running")
    run_prog = progreso_running(df_act)
    if run_prog.empty:
        st.info("Aún no hay datos de carrera para mostrar progreso.")
    else:
        fig_run = px.line(
            run_prog,
            x="week",
            y="km_semana",
            markers=True,
            title="Kilómetros por semana",
            labels={"week": "Semana", "km_semana": "Km"},
        )
        fig_run.update_traces(line_color="#0f766e")
        st.plotly_chart(fig_run, use_container_width=True)

    st.divider()
    st.subheader("🛡️ Radar Antilesiones y Técnica")
    radar = resumen_usuario_para_plan(user_actual)
    t1, t2, t3, t4, t5 = st.columns(5)
    t1.metric("Cadencia", "—" if radar["cadencia_media"] is None else f"{radar['cadencia_media']:.0f} spm")
    t2.metric("Zancada", "—" if radar["longitud_zancada_m"] is None else f"{radar['longitud_zancada_m']:.2f} m")
    t3.metric("Contacto", "—" if radar["tiempo_contacto"] is None else f"{radar['tiempo_contacto']:.0f} ms")
    t4.metric("Osc. vertical", "—" if radar["oscilacion_vertical"] is None else f"{radar['oscilacion_vertical']:.1f} cm")
    t5.metric("Potencia", "—" if radar["potencia_media_w"] is None else f"{radar['potencia_media_w']:.0f} W")

    avisos_radar = []
    if radar["cadencia_media"] is not None and radar["longitud_zancada_m"] is not None and radar["cadencia_media"] < 170 and radar["longitud_zancada_m"] > 1.15:
        avisos_radar.append("Overstride probable: cadencia baja con zancada larga. Conviene técnica y fuerza reactiva.")
    if radar["oscilacion_vertical"] is not None and radar["oscilacion_vertical"] > 12:
        avisos_radar.append("Rebote alto: añade core y trabajo de rigidez de tobillo para economizar carrera.")
    if radar["tiempo_contacto"] is not None and radar["tiempo_contacto"] > 290:
        avisos_radar.append("Tiempo de contacto elevado: señal de fatiga o pérdida de elasticidad.")
    if avisos_radar:
        for aviso in avisos_radar:
            st.warning(aviso)
    else:
        st.caption("Sin alertas técnicas importantes en los últimos datos Garmin sincronizados.")

    st.divider()
    st.subheader("🚦 Semáforo Diario Garmin")
    s1, s2, s3, s4, s5, s6 = st.columns(6)
    s1.metric("HRV", "—" if radar["hrv_actual"] is None else f"{radar['hrv_actual']:.0f} ms")
    s2.metric("Readiness", "—" if radar["training_readiness"] is None else f"{radar['training_readiness']}/100")
    s3.metric("Body Battery", "—" if radar["body_battery"] is None else f"{radar['body_battery']}/100")
    s4.metric("Recup.", "—" if radar["recovery_hours"] is None else f"{radar['recovery_hours']:.0f} h")
    s5.metric("RHR", "—" if radar["fc_reposo"] is None else f"{radar['fc_reposo']} bpm")
    s6.metric("SpO2", "—" if radar["spo2"] is None else f"{radar['spo2']:.0f}%")

    semaforo = []
    if radar["training_readiness"] is not None and radar["training_readiness"] < 40:
        semaforo.append("Readiness bajo: cancela intensidad hoy.")
    if radar["body_battery"] is not None and radar["body_battery"] < 35:
        semaforo.append("Body Battery bajo: mejor sesión regenerativa o descanso.")
    if radar["fc_reposo"] is not None and radar["fc_reposo"] >= 60:
        semaforo.append("RHR alta respecto a valores normales: posible mala asimilación o fatiga.")
    if radar["estres_vital"] is not None and radar["estres_vital"] >= 60:
        semaforo.append("Estrés alto: la carga del día debería bajar aunque el plan dijera otra cosa.")
    if semaforo:
        for aviso in semaforo:
            st.warning(aviso)
    else:
        st.caption("Semáforo sin banderas rojas importantes en la última sincronización.")

    st.subheader("🏋️ Progreso de gimnasio por grupo muscular")
    gym_prog = progreso_fuerza_grupos(df_fuerza)
    if gym_prog.empty:
        st.info("Aún no hay datos de fuerza para construir la gráfica de grupos musculares.")
    else:
        color_map = {
            "gluteos": "#ec4899",
            "espalda biceps": "#0ea5e9",
            "isquios": "#f97316",
            "cuadriceps": "#22c55e",
            "gemelos": "#f59e0b",
            "triceps": "#8b5cf6",
            "hombro": "#ef4444",
            "abdominales": "#14b8a6",
        }
        fig_gym = px.line(
            gym_prog,
            x="fecha_dt",
            y="volumen",
            color="grupo",
            markers=True,
            title="Volumen por grupo muscular",
            color_discrete_map=color_map,
            labels={"fecha_dt": "Fecha", "volumen": "Volumen", "grupo": "Grupo"},
        )
        st.plotly_chart(fig_gym, use_container_width=True)

    # Visualización de Sueño
    if not df_sueno.empty:
        st.divider()
        st.subheader("🌙 Calidad del Sueño (Última semana)")
        df_sueno['fecha_f'] = pd.to_datetime(df_sueno['fecha']).dt.strftime('%d-%m')
        st.plotly_chart(px.bar(df_sueno.sort_values('fecha'), x='fecha_f', y='horas_totales', color='score', title="Horas y Score de Sueño"), use_container_width=True)

        d1, d2, d3, d4 = st.columns(4)
        d1.metric("Sueño profundo", "—" if radar["sleep_profundo_7d"] is None else f"{radar['sleep_profundo_7d']:.2f} h")
        d2.metric("Sueño REM", "—" if radar["sleep_rem_7d"] is None else f"{radar['sleep_rem_7d']:.2f} h")
        d3.metric("Vigilia", "—" if radar["sleep_vigilia_7d"] is None else f"{radar['sleep_vigilia_7d']:.2f} h")
        d4.metric("Despertares", "—" if radar["despertares_7d"] is None else f"{radar['despertares_7d']:.1f}")

    # ── Entrenamientos conjuntos Malena + Dani ────────────────────────────
    st.divider()
    st.subheader("👫 Entrenamientos conjuntos — Malena & Dani")
    st.caption("Rosa: Malena · Azul celeste: Dani · Verde claro: coinciden los dos.")

    hoy_conj = datetime.now().date()
    semana_conj_def = hoy_conj - timedelta(days=hoy_conj.weekday())
    semana_conj = st.date_input(
        "Semana del calendario conjunto",
        value=semana_conj_def,
        key="semana_conjunto",
    )
    semana_conj_dt = datetime.combine(semana_conj, datetime.min.time())
    plan_conjunto = _cargar_plan_conjunto(semana_conj_dt)

    MALENA_ID, DANI_ID = 1, 2
    TIPOS_ACTIVOS = {"Carrera", "Fuerza", "Mixto", "Cardio alternativo"}
    nombres_dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    cols_conj = st.columns(7)

    for i in range(7):
        fecha_dia = (semana_conj_dt + timedelta(days=i)).strftime("%Y-%m-%d")
        malena_rows = plan_conjunto[
            (plan_conjunto["usuario_id"] == MALENA_ID) & (plan_conjunto["fecha"] == fecha_dia)
        ] if not plan_conjunto.empty else pd.DataFrame()
        dani_rows = plan_conjunto[
            (plan_conjunto["usuario_id"] == DANI_ID) & (plan_conjunto["fecha"] == fecha_dia)
        ] if not plan_conjunto.empty else pd.DataFrame()

        malena_activa = not malena_rows.empty and malena_rows.iloc[0]["tipo"] in TIPOS_ACTIVOS
        dani_activo   = not dani_rows.empty   and dani_rows.iloc[0]["tipo"] in TIPOS_ACTIVOS
        coincide = malena_activa and dani_activo

        if coincide:
            bg = "#bbf7d0"       # verde claro — coinciden
            borde = "2px solid #16a34a"
        elif malena_activa:
            bg = "#fce7f3"       # rosa pastel
            borde = "1px solid #f9a8d4"
        elif dani_activo:
            bg = "#bae6fd"       # azul celeste
            borde = "1px solid #7dd3fc"
        else:
            bg = "#f8fafc"
            borde = "1px dashed #cbd5e1"

        malena_txt = malena_rows.iloc[0]["sesion"] if not malena_rows.empty else "—"
        dani_txt   = dani_rows.iloc[0]["sesion"]   if not dani_rows.empty   else "—"

        with cols_conj[i]:
            st.markdown(
                f"""<div style='background:{bg};border:{borde};border-radius:10px;
                    padding:10px 8px;min-height:120px;font-size:0.8rem;'>
                    <div style='font-weight:700;color:#0f172a;margin-bottom:4px;'>{nombres_dias[i]}</div>
                    <div style='color:#be185d;'>🙋‍♀️ {malena_txt[:28]}</div>
                    <div style='color:#0369a1;margin-top:4px;'>🙋‍♂️ {dani_txt[:28]}</div>
                    {'<div style="margin-top:6px;font-size:0.72rem;color:#15803d;font-weight:600;">✔ Juntos</div>' if coincide else ''}
                </div>""",
                unsafe_allow_html=True,
            )

# (El resto de secciones se mantienen igual...)

# ==========================================
# PESTAÑA 2: BIBLIOTECA CIENTÍFICA
# ==========================================
elif menu == "Biblioteca Científica":
    st.title("📚 Biblioteca Científica")
    st.caption(
        "Los archivos se guardan en disco y en la base de datos solo se almacena metadato + texto/resumen. "
        "Así evitas cargar Turso con binarios pesados y la IA sí puede usar el contenido."
    )

    alcance = st.radio(
        "Alcance del estudio",
        ["Solo este perfil", "Compartido para ambos"],
        horizontal=True,
    )
    categoria = st.selectbox(
        "Categoría",
        ["running", "fuerza", "ciclo menstrual", "nutrición", "recuperación", "psicología deportiva", "lesiones"],
    )
    uploaded = st.file_uploader(
        "Sube PDF, TXT o MD",
        type=["pdf", "txt", "md"],
        accept_multiple_files=False,
    )
    resumen_manual = st.text_area(
        "Resumen manual opcional",
        placeholder="Si quieres, resume el paper con tus palabras y eso tendrá prioridad sobre el resumen automático.",
        height=100,
    )
    if st.button("Guardar estudio", disabled=uploaded is None):
        if uploaded is not None:
            usuario_estudio = 0 if alcance == "Compartido para ambos" else user_actual
            try:
                guardar_estudio_referencia(usuario_estudio, uploaded, categoria, resumen_manual)
                st.success("Estudio guardado. La IA ya podrá usarlo como contexto.")
                st.rerun()
            except Exception as e:
                st.error(f"No se pudo guardar el estudio: {e}")

    conn = get_db_connection()
    try:
        estudios = pd.read_sql_query(
            """
            SELECT id, usuario_id, titulo, categoria, resumen, creado_en
            FROM estudios_referencia
            WHERE usuario_id IN (?, 0)
            ORDER BY creado_en DESC
            """,
            conn,
            params=(user_actual,),
        )
    except Exception:
        estudios = pd.DataFrame()
    finally:
        conn.close()

    if estudios.empty:
        st.info("Todavía no hay estudios subidos.")
    else:
        for _, est in estudios.iterrows():
            scope = "Compartido" if int(est["usuario_id"]) == 0 else "Perfil"
            with st.expander(f"{est['titulo']} · {est['categoria']} · {scope}"):
                st.caption(str(est["creado_en"]))
                st.write(est["resumen"] or "Sin resumen disponible.")

# ==========================================
# PESTAÑA 3: CICLO MENSTRUAL
# ==========================================
elif menu == "Ciclo Menstrual":
    if user_actual != 1:
        st.info("Esta sección no está disponible para este perfil.")
        st.stop()
    st.title("Ciclo Menstrual")
    with st.form("fisio_form"):
        fecha = st.date_input("Fecha")
        fase = st.selectbox("Fase del Ciclo", ["Fase Folicular", "Fase Ovulatoria", "Fase Lútea", "No Aplica"])
        fatiga = st.slider("Nivel de Fatiga (1-10)", 1, 10, 5)
        notas = st.text_area("Notas / Molestias / Dolor")
        submit_fisio = st.form_submit_button("Guardar Registro")
        
    if submit_fisio:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO diario_fisiologia (usuario_id, fecha, fase_ciclo, fatiga_subjetiva, dolor_notas) VALUES (?, ?, ?, ?, ?)",
                       (user_actual, str(fecha), fase, fatiga, notas))
        conn.commit()
        conn.close()
        st.success("Registro guardado correctamente.")

    conn = get_db_connection()
    df_fisio = pd.read_sql_query(
        "SELECT fecha, fase_ciclo, fatiga_subjetiva, dolor_notas FROM diario_fisiologia WHERE usuario_id = ? ORDER BY fecha",
        conn,
        params=(user_actual,),
    )
    conn.close()

    if df_fisio.empty:
        st.info("Aún no hay datos para visualizar calendario y predicción del ciclo.")
    else:
        df_valid = df_fisio[df_fisio["fase_ciclo"] != "No Aplica"].copy()
        ciclo_df, ciclo_estimado = predecir_fases_ciclo(df_valid, horizonte_dias=120)

        st.divider()
        c1, c2 = st.columns([0.35, 0.65])
        with c1:
            st.metric("Ciclo estimado", f"{ciclo_estimado} días")
        with c2:
            st.caption("Borde sólido: registro real. Borde discontinuo: predicción.")

        hoy = datetime.now().date()
        mes_base = st.date_input("Mes del calendario", value=hoy.replace(day=1), key="mes_ciclo")
        render_calendario_ciclo(ciclo_df, mes_base.year, mes_base.month)

        st.divider()
        st.subheader("Predicción de próximos ciclos")
        pred_only = ciclo_df[ciclo_df["origen"] == "Predicho"].copy()
        prox = pred_only[pred_only["fase_ciclo"] == "Fase Folicular"].head(4)
        if prox.empty:
            st.caption("No hay predicción disponible todavía.")
        else:
            prox["fecha"] = pd.to_datetime(prox["fecha"]).dt.strftime("%d-%m-%Y")
            st.dataframe(prox[["fecha", "fase_ciclo"]], use_container_width=True)

# ==========================================
# PESTAÑA 4: CONSULTORIO VIRTUAL (IA)
# ==========================================
elif menu == "Asistente Virtual":
    st.title("Asistente Virtual")
    if obtener_consejo is None:
        st.error("Error: No se ha podido cargar ai_coach.py. Revisa que el archivo exista y esté correcto.")
    else:
        # Extraer contexto para la IA
        conn = get_db_connection()
        try:
            df_actividades = pd.read_sql_query(
                "SELECT fecha, tipo_deporte, distancia_m, ritmo_medio, fc_media FROM actividades_garmin WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 3",
                conn,
                params=(user_actual,),
            )
            df_fisio = pd.read_sql_query(
                "SELECT fecha, fase_ciclo, fatiga_subjetiva, dolor_notas FROM diario_fisiologia WHERE usuario_id = ? ORDER BY fecha DESC LIMIT 1",
                conn,
                params=(user_actual,),
            )
            estudios_ctx = contexto_estudios(user_actual)
            contexto = f"Últimas actividades: {df_actividades.to_dict('records')}. Estado fisiológico: {df_fisio.to_dict('records')}. Estudios científicos subidos: {estudios_ctx}."
        except:
            contexto = "Aún no hay datos suficientes registrados."
        conn.close()

        # Interfaz de Chat
        if "mensajes" not in st.session_state:
            st.session_state.mensajes = []

        # Mostrar historial de mensajes
        for msg in st.session_state.mensajes:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Input del usuario
        duda = st.chat_input("Escribe tu duda (ej. ¿Cómo ves mi carga de entrenamiento en esta fase de mi ciclo?)...")
        if duda:
            # Mostrar lo que escribió el usuario
            with st.chat_message("user"):
                st.markdown(duda)
            st.session_state.mensajes.append({"role": "user", "content": duda})
            
            # Mostrar la respuesta de la IA
            with st.chat_message("assistant"):
                with st.spinner("Analizando tus datos biométricos..."):
                    try:
                        # Ojo: pasamos duda y contexto. Si tu ai_coach pide más parámetros, avisame.
                        respuesta = obtener_consejo(duda, contexto) 
                        st.markdown(respuesta)
                        st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
                    except Exception as e:
                        st.error(f"Error al procesar la respuesta: {e}")
elif menu == "Diario de Fuerza":
    st.title("🏋️‍♀️ Diario de Fuerza")

    if "resultado_ia" not in st.session_state:
        st.session_state.resultado_ia = None
    if "nota_fuerza" not in st.session_state:
        st.session_state.nota_fuerza = ""
    if "sesiones_detectadas" not in st.session_state:
        st.session_state.sesiones_detectadas = []   # lista de (fecha, datos_ia)

    st.caption(
        "Escribe en lenguaje natural. Puedes incluir varias fechas en un mismo texto: "
        "'hoy he hecho búlgaras y ayer abs' o 'el martes hice sentadilla y hoy prensa'."
    )
    nota_fuerza = st.text_area(
        "Entreno libre",
        height=130,
        key="nota_fuerza",
        placeholder="Ej: hoy hice glute bridge 4x10 80kg, y ayer remo 4x8 40kg y press militar 3x10 18kg",
    )

    if nota_fuerza.strip():
        segmentos = _dividir_nota_por_fechas(nota_fuerza)
        if len(segmentos) > 1:
            st.info(f"📅 Se detectaron **{len(segmentos)} bloques temporales** en tu texto — se guardarán como sesiones separadas:")
            for marca, frag in segmentos:
                fecha_seg, motivo_seg = extraer_fecha_historica(frag if marca else nota_fuerza)
                st.caption(f"• **{fecha_seg.strftime('%d-%m-%Y')}** ({motivo_seg}): _{frag[:80]}…_" if len(frag) > 80 else f"• **{fecha_seg.strftime('%d-%m-%Y')}**: _{frag}_")
        else:
            fecha_auto, motivo = extraer_fecha_historica(nota_fuerza)
            st.caption(f"📅 Fecha detectada: **{fecha_auto.strftime('%d-%m-%Y')}** — {motivo}")

    if st.button("Procesar entrenamiento con IA"):
        if nota_fuerza.strip():
            segmentos = _dividir_nota_por_fechas(nota_fuerza)
            sesiones_prep = []
            with st.spinner("Analizando entrenamiento..."):
                for marca, frag in segmentos:
                    texto_seg = frag if marca else nota_fuerza
                    fecha_seg, _ = extraer_fecha_historica(texto_seg)
                    res = procesar_nota_fuerza(texto_seg)
                    sesiones_prep.append((fecha_seg, res, texto_seg))
            st.session_state.sesiones_detectadas = sesiones_prep
            st.session_state.resultado_ia = True
            st.rerun()

    if st.session_state.resultado_ia and st.session_state.sesiones_detectadas:
        todas_ok = all(s[1]["exito"] and len(s[1]["datos"]) > 0 for s in st.session_state.sesiones_detectadas)

        if not todas_ok:
            for fecha_s, res_s, _ in st.session_state.sesiones_detectadas:
                if not res_s["exito"]:
                    st.error(f"❌ No se pudo procesar el bloque del {fecha_s.strftime('%d-%m-%Y')}:")
                    st.code(res_s["raw"])
        else:
            for fecha_s, res_s, _ in st.session_state.sesiones_detectadas:
                st.success(f"✅ {fecha_s.strftime('%d-%m-%Y')} — {len(res_s['datos'])} ejercicios detectados")
                st.dataframe(res_s["datos"], use_container_width=True)

            n_sesiones = len(st.session_state.sesiones_detectadas)
            etiqueta = f"🚀 Guardar {n_sesiones} sesión{'es' if n_sesiones > 1 else ''}"
            if st.button(etiqueta):
                conn = get_db_connection()
                try:
                    for fecha_s, res_s, nota_orig_s in st.session_state.sesiones_detectadas:
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO sesiones_fuerza (usuario_id, fecha, nota_original, resumen, created_at)
                            VALUES (?, ?, ?, ?, ?)
                            """,
                            (
                                user_actual,
                                fecha_s.strftime("%Y-%m-%d"),
                                nota_orig_s,
                                f"{len(res_s['datos'])} ejercicios",
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            ),
                        )
                        sesion_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        for ej in res_s["datos"]:
                            conn.execute(
                                """
                                INSERT INTO ejercicios_fuerza
                                (sesion_id, ejercicio, peso, series, repeticiones, grupo_muscular, musculo_principal, rpe)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    sesion_id,
                                    ej.get("ejercicio", ""),
                                    float(ej.get("peso", 0) or 0),
                                    int(ej.get("series", 0) or 0),
                                    int(ej.get("repeticiones", 0) or 0),
                                    ej.get("grupo_muscular", "Tren Inferior"),
                                    ej.get("musculo_principal", "Varios"),
                                    int(ej.get("rpe", 5) or 5),
                                ),
                            )
                    conn.commit()
                    st.success(f"✅ {n_sesiones} sesión{'es' if n_sesiones > 1 else ''} guardada{'s' if n_sesiones > 1 else ''} correctamente.")
                    st.session_state.resultado_ia = None
                    st.session_state.sesiones_detectadas = []
                    st.rerun()
                except Exception as e:
                    st.error(f"Error SQL guardando sesión: {e}")
                finally:
                    conn.close()

    st.divider()
    st.subheader("📚 Historial por entrenamientos")
    conn = get_db_connection()
    try:
        sesiones = pd.read_sql_query(
            """
            SELECT id, fecha, resumen, created_at
            FROM sesiones_fuerza
            WHERE usuario_id = ?
            ORDER BY fecha DESC, id DESC
            LIMIT 25
            """,
            conn,
            params=(user_actual,),
        )

        if sesiones.empty:
            st.info("Aún no hay sesiones guardadas.")
        else:
            for _, ses in sesiones.iterrows():
                fecha_txt = pd.to_datetime(ses["fecha"]).strftime("%d-%m-%Y")
                with st.expander(f"{fecha_txt} · {ses['resumen']}"):
                    detalle = pd.read_sql_query(
                        """
                        SELECT ejercicio, series, repeticiones, peso, rpe, grupo_muscular, musculo_principal
                        FROM ejercicios_fuerza
                        WHERE sesion_id = ?
                        ORDER BY id
                        """,
                        conn,
                        params=(int(ses["id"]),),
                    )
                    st.dataframe(detalle, use_container_width=True)
    except Exception as e:
        st.error(f"No se pudo cargar historial de sesiones: {e}")
    finally:
        conn.close()

# ==========================================
# PESTAÑA 5: ENTRENADOR PERSONAL
# ==========================================
elif menu == "Entrenador Personal":
    st.title("🎯 Entrenador Personal Premium")

    tab_checkin, tab_plan, tab_lesiones = st.tabs(
        ["📊 Check-in Diario", "🧠 Generar Plan Semanal", "🩹 Lesiones y Prevención"]
    )

    # ── Tab 1: Check-in diario ────────────────────────────────────────────
    with tab_checkin:
        st.subheader("Semáforo diario Garmin")
        st.caption(
            "Estos datos se sincronizan directamente desde Garmin. "
            "No hace falta que el usuario los meta a mano."
        )
        cred = obtener_credenciales_garmin(user_actual)
        if cred and cred[0]:
            if st.button("🔄 Sincronizar biométricos Garmin", key="sync_garmin_semáforo"):
                with st.spinner("Sincronizando HRV, readiness, body battery, sueño y técnica..."):
                    try:
                        email, p_enc = cred
                        pw = desencriptar_password(p_enc)
                        sincronizar_biometricos_garmin(email, pw, user_actual, dias=7)
                        st.success("✅ Datos Garmin actualizados.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"No se pudo sincronizar Garmin: {e}")
        else:
            st.warning("Configura tus credenciales de Garmin en el perfil para activar el semáforo automático.")

        datos_hoy = resumen_usuario_para_plan(user_actual)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("HRV", "—" if datos_hoy["hrv_actual"] is None else f"{datos_hoy['hrv_actual']:.0f} ms")
        c2.metric("Training Readiness", "—" if datos_hoy["training_readiness"] is None else f"{datos_hoy['training_readiness']}/100")
        c3.metric("Body Battery", "—" if datos_hoy["body_battery"] is None else f"{datos_hoy['body_battery']}/100")
        c4.metric("Recuperación", "—" if datos_hoy["recovery_hours"] is None else f"{datos_hoy['recovery_hours']:.0f} h")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("FC reposo", "—" if datos_hoy["fc_reposo"] is None else f"{datos_hoy['fc_reposo']} bpm")
        c6.metric("Estrés", "—" if datos_hoy["estres_vital"] is None else f"{datos_hoy['estres_vital']}/100")
        c7.metric("SpO2", "—" if datos_hoy["spo2"] is None else f"{datos_hoy['spo2']:.0f}%")
        c8.metric("Sleep Score", "—" if datos_hoy["sueno_score_7d"] is None else f"{datos_hoy['sueno_score_7d']:.0f}")

        c9, c10, c11, c12 = st.columns(4)
        c9.metric("Cadencia", "—" if datos_hoy["cadencia_media"] is None else f"{datos_hoy['cadencia_media']:.0f} spm")
        c10.metric("Zancada", "—" if datos_hoy["longitud_zancada_m"] is None else f"{datos_hoy['longitud_zancada_m']:.2f} m")
        c11.metric("Contacto suelo", "—" if datos_hoy["tiempo_contacto"] is None else f"{datos_hoy['tiempo_contacto']:.0f} ms")
        c12.metric("Osc. vertical", "—" if datos_hoy["oscilacion_vertical"] is None else f"{datos_hoy['oscilacion_vertical']:.1f} cm")

        conn = get_db_connection()
        try:
            histo = pd.read_sql_query(
                """
                SELECT fecha,
                       hrv_ms AS "HRV",
                       training_readiness AS "Readiness",
                       body_battery AS "Body Battery",
                       recovery_hours AS "Recuperación h",
                       fc_reposo AS "FC reposo",
                       estres_vital AS "Estrés",
                       spo2 AS "SpO2",
                       sleep_score AS "Sleep score",
                       cadencia_media AS "Cadencia",
                       longitud_zancada_m AS "Zancada m",
                       tiempo_contacto_ms AS "Contacto ms",
                       oscilacion_vertical_cm AS "Osc. vertical cm",
                       potencia_media_w AS "Potencia W"
                FROM datos_biometricos_premium
                WHERE usuario_id = ?
                ORDER BY fecha DESC LIMIT 7
                """,
                conn, params=(user_actual,),
            )
            if not histo.empty:
                st.markdown("##### Últimos 7 días sincronizados")
                st.dataframe(histo, use_container_width=True, hide_index=True)

            sueno_det = pd.read_sql_query(
                """
                SELECT fecha,
                       horas_totales AS "Sueño total h",
                       sleep_profundo_horas AS "Profundo h",
                       sleep_rem_horas AS "REM h",
                       sleep_vigilia_horas AS "Vigilia h",
                       despertares AS "Despertares",
                       score AS "Sleep score"
                FROM datos_sueno
                WHERE usuario_id = ?
                ORDER BY fecha DESC LIMIT 7
                """,
                conn, params=(user_actual,),
            )
            if not sueno_det.empty:
                st.markdown("##### Reparación nocturna Garmin")
                st.dataframe(sueno_det, use_container_width=True, hide_index=True)
        except Exception:
            pass
        finally:
            conn.close()

    # ── Tab 2: Generar plan semanal ───────────────────────────────────────
    with tab_plan:
        datos_premium = resumen_usuario_para_plan(user_actual)

        # Dashboard de señales
        a1, a2, a3, a4, a5 = st.columns(5)
        hrv_val = datos_premium["hrv_actual"]
        hrv_t   = datos_premium["hrv_tendencia"] or 0.0
        a1.metric("HRV actual", "—" if hrv_val is None else f"{hrv_val:.0f} ms",
                  delta=None if hrv_t == 0 else f"{hrv_t:+.1f}")
        a2.metric("FC reposo", "—" if datos_premium["fc_reposo"] is None else f"{datos_premium['fc_reposo']} bpm")
        a3.metric("Días mal sueño (7d)", datos_premium["dias_mal_sueno"], delta_color="inverse")
        a4.metric("Estrés vital", f"{datos_premium['estres_vital']}/100")
        a5.metric("RPE último", "—" if datos_premium["rpe_ultima"] is None else f"{datos_premium['rpe_ultima']}/10")

        b1, b2, b3, b4 = st.columns(4)
        b1.metric("Training Readiness", "—" if datos_premium["training_readiness"] is None else f"{datos_premium['training_readiness']}/100")
        b2.metric("Body Battery", "—" if datos_premium["body_battery"] is None else f"{datos_premium['body_battery']}/100")
        b3.metric("Recuperación", "—" if datos_premium["recovery_hours"] is None else f"{datos_premium['recovery_hours']:.0f} h")
        b4.metric("Potencia carrera", "—" if datos_premium["potencia_media_w"] is None else f"{datos_premium['potencia_media_w']:.0f} W")

        ratio = datos_premium.get("ratio_ctl_atl")
        if ratio:
            color = "🟢" if ratio < 1.3 else ("🟡" if ratio < 1.5 else "🔴")
            label = "OK" if ratio < 1.3 else ("Precaución" if ratio < 1.5 else "Riesgo sobreentrenamiento")
            st.caption(f"{color} Ratio carga aguda/crónica: **{ratio:.2f}** — {label}")

        fase = datos_premium.get("fase_ciclo_actual")
        if fase:
            st.caption(f"♀️ Fase del ciclo: **{fase}**")

        lesiones_act = datos_premium.get("lesiones_activas") or []
        if lesiones_act:
            st.caption(f"🩹 Lesiones activas: **{', '.join(lesiones_act)}**")

        st.divider()
        hoy = datetime.now().date()
        inicio_default = hoy - timedelta(days=hoy.weekday())
        semana_inicio = st.date_input("Semana a planificar (inicio lunes)", value=inicio_default)

        # Opción de coordinar con la pareja
        otro_uid = 2 if user_actual == 1 else 1
        otro_nombre = "Dani" if otro_uid == 2 else "Malena"
        coordinar = st.checkbox(
            f"👫 Coordinar con el plan de {otro_nombre} (intentar coincidir días de entreno)",
            value=True,
        )

        col_a, col_b = st.columns([0.35, 0.65])
        with col_a:
            generar = st.button("🧠 Generar plan premium", use_container_width=True)
        with col_b:
            st.info("El plan se adapta a tu HRV, sueño, carga, lesiones, ciclo menstrual, estrés vital y RPE.")

        if generar:
            semana_dt = datetime.combine(semana_inicio, datetime.min.time())
            plan_pareja_df = None
            if coordinar:
                plan_pareja_df = cargar_plan_semanal(otro_uid, semana_dt)
                if plan_pareja_df.empty:
                    plan_pareja_df = None
            plan, alertas = generar_plan_semanal(perfil, datos_premium, semana_dt, plan_pareja=plan_pareja_df)
            guardar_plan_semanal(user_actual, semana_dt, plan)
            st.session_state["alertas_plan"] = alertas
            st.session_state["plan_generado_csv"] = plan.to_csv(index=False, sep=";")
            st.session_state["semana_plan_dt"] = semana_dt
            st.success("✅ Plan semanal guardado.")
            st.rerun()

        if st.session_state.get("alertas_plan"):
            for alerta in st.session_state["alertas_plan"]:
                st.warning(alerta)

        plan_guardado = cargar_plan_semanal(
            user_actual, datetime.combine(semana_inicio, datetime.min.time())
        )
        if plan_guardado.empty:
            st.info("Todavía no hay plan para esta semana. Pulsa en 'Generar plan premium'.")
        else:
            plan_view = plan_guardado.copy()
            plan_view["fecha"] = pd.to_datetime(plan_view["fecha"]).dt.strftime("%d-%m-%Y")
            st.dataframe(plan_view, use_container_width=True, hide_index=True)

            # ── Feedback post-generación ──────────────────────────────────
            st.divider()
            st.markdown("##### 💬 ¿Quieres cambiar algo del plan?")
            st.caption(
                "Dile a la IA en texto libre qué quieres ajustar: "
                "'ese día no me viene bien hacer pierna, cámbialo al martes' o "
                "'el miércoles cambia carrera por descanso'."
            )
            feedback_txt = st.text_area(
                "Feedback al plan",
                placeholder="Ej: el jueves no puedo entrenar, muévelo al viernes",
                height=80,
                key="feedback_plan",
            )
            if st.button("🔄 Aplicar cambios con IA", key="btn_feedback"):
                if feedback_txt.strip():
                    from ai_coach import ajustar_plan_con_feedback
                    plan_csv = st.session_state.get("plan_generado_csv") or plan_guardado.to_csv(index=False, sep=";")
                    estudios_ctx = contexto_estudios(user_actual)
                    resumen_perf = (
                        f"Objetivo: {perfil.get('objetivo')}, nivel: {perfil.get('nivel')}, "
                        f"días carrera: {perfil.get('carrera')}, días fuerza: {perfil.get('fuerza')}. "
                        f"Estudios científicos relevantes: {estudios_ctx}"
                    )
                    with st.spinner("Ajustando plan..."):
                        resultado = ajustar_plan_con_feedback(plan_csv, feedback_txt, resumen_perf)
                    if resultado["exito"] and resultado["datos"]:
                        nuevo_plan = pd.DataFrame(resultado["datos"])
                        # Normalizar columnas al esquema esperado
                        col_map = {
                            "dia": "dia", "fecha": "fecha", "tipo": "tipo",
                            "sesion": "sesion", "detalles": "detalles",
                            "duracion_min": "duracion_min", "intensidad": "intensidad",
                        }
                        for col in col_map:
                            if col not in nuevo_plan.columns:
                                nuevo_plan[col] = ""
                        semana_fb_dt = st.session_state.get(
                            "semana_plan_dt",
                            datetime.combine(semana_inicio, datetime.min.time()),
                        )
                        guardar_plan_semanal(user_actual, semana_fb_dt, nuevo_plan[list(col_map.keys())])
                        st.session_state["plan_generado_csv"] = nuevo_plan.to_csv(index=False, sep=";")
                        st.success("✅ Plan actualizado con tu feedback.")
                        st.rerun()
                    else:
                        st.error("La IA no pudo procesar el feedback. Inténtalo de nuevo.")
                        if resultado.get("raw"):
                            st.code(resultado["raw"])

    # ── Tab 3: Lesiones ───────────────────────────────────────────────────
    with tab_lesiones:
        st.subheader("Historial y prevención de lesiones")
        st.caption(
            "Las lesiones activas modifican automáticamente el plan: "
            "sustituye carreras, elimina cargas de impacto y añade trabajo preventivo."
        )
        with st.form("lesion_form"):
            lc1, lc2 = st.columns(2)
            with lc1:
                zona_les = st.text_input(
                    "Zona lesionada", placeholder="Ej: rodilla izquierda, fascia plantar, isquio derecho"
                )
                tipo_les = st.selectbox("Tipo", ["sobreuso", "aguda", "prevención"])
            with lc2:
                fecha_les = st.date_input("Fecha inicio", value=datetime.now().date())
                notas_les = st.text_area("Notas / contexto", height=70)
            if st.form_submit_button("➕ Registrar lesión"):
                if zona_les.strip():
                    conn = get_db_connection()
                    conn.execute(
                        "INSERT INTO historial_lesiones (usuario_id, fecha_inicio, zona, tipo, activa, notas) "
                        "VALUES (?, ?, ?, ?, 1, ?)",
                        (user_actual, str(fecha_les), zona_les.strip(), tipo_les, notas_les),
                    )
                    conn.commit()
                    conn.close()
                    st.success("✅ Lesión registrada.")
                    st.rerun()
                else:
                    st.error("Indica la zona lesionada.")

        conn = get_db_connection()
        try:
            les_df = pd.read_sql_query(
                "SELECT id, fecha_inicio, zona, tipo, activa, notas "
                "FROM historial_lesiones WHERE usuario_id = ? "
                "ORDER BY activa DESC, fecha_inicio DESC",
                conn, params=(user_actual,),
            )
            if les_df.empty:
                st.info("Sin lesiones registradas.")
            else:
                for _, row in les_df.iterrows():
                    estado = "🔴 Activa" if row["activa"] else "✅ Resuelta"
                    with st.expander(f"{estado} · {row['zona']} ({row['fecha_inicio']})"):
                        st.write(f"**Tipo:** {row['tipo']}  |  **Notas:** {row['notas'] or '—'}")
                        if row["activa"]:
                            if st.button("Marcar como resuelta", key=f"resol_{row['id']}"):
                                conn.execute(
                                    "UPDATE historial_lesiones SET activa = 0, fecha_fin = ? WHERE id = ?",
                                    (str(datetime.now().date()), int(row["id"])),
                                )
                                conn.commit()
                                st.rerun()
        except Exception as e:
            st.error(f"Error cargando lesiones: {e}")
        finally:
            conn.close()


# ==========================================
# PESTAÑA 6: CALENDARIO
# ==========================================
elif menu == "Calendario":
    st.title("🗓️ Calendario de Entrenamientos")
    st.caption("Vista semanal de tus sesiones planificadas.")

    hoy = datetime.now().date()
    inicio_default = hoy - timedelta(days=hoy.weekday())
    semana_cal = st.date_input("Semana del calendario", value=inicio_default, key="semana_cal")

    plan_cal = cargar_plan_semanal(user_actual, datetime.combine(semana_cal, datetime.min.time()))
    if plan_cal.empty:
        st.info("No hay sesiones guardadas para esta semana. Ve a 'Entrenador Personal' para generarlas.")
    else:
        plan_cal = plan_cal.copy()
        plan_cal["fecha_dt"] = pd.to_datetime(plan_cal["fecha"])
        plan_cal["dia_nombre"] = plan_cal["fecha_dt"].dt.day_name()

        colores = {
            "Carrera": "#0f766e",
            "Fuerza": "#0ea5e9",
            "Mixto": "#f97316",
            "Recuperacion": "#64748b",
        }

        st.markdown("### Semana en tarjetas")
        nombres = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        trad = {
            "Monday": "Lunes",
            "Tuesday": "Martes",
            "Wednesday": "Miercoles",
            "Thursday": "Jueves",
            "Friday": "Viernes",
            "Saturday": "Sabado",
            "Sunday": "Domingo",
        }

        cols = st.columns(7)
        for i, d in enumerate(nombres):
            with cols[i]:
                sesion = plan_cal[plan_cal["dia_nombre"] == d]
                st.markdown(f"**{trad[d]}**")
                if sesion.empty:
                    st.caption("Sin sesion")
                else:
                    fila = sesion.iloc[0]
                    color = colores.get(fila["tipo"], "#334155")
                    st.markdown(
                        f"""
                        <div style='border-left:6px solid {color}; padding:8px 10px; border-radius:8px; background:#f8fafc;'>
                            <div style='font-size:0.78rem; color:#475569;'>{fila['fecha_dt'].strftime('%d/%m')}</div>
                            <div style='font-weight:700; color:#0f172a; margin:2px 0;'>{fila['sesion']}</div>
                            <div style='font-size:0.82rem; color:#334155;'>{fila['duracion_min']} min · {fila['intensidad']}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

        st.divider()
        st.markdown("### Vista detallada")
        plan_out = plan_cal[["fecha", "tipo", "sesion", "duracion_min", "intensidad", "detalles"]].copy()
        plan_out["fecha"] = pd.to_datetime(plan_out["fecha"]).dt.strftime("%d-%m-%Y")
        st.dataframe(plan_out, use_container_width=True)

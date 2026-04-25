"""
src/core/diario_ui_helpers.py — Helpers UI Tab Entreno libre.
Calendario clickable, sesiones del día, chips, formateo.
Sin lógica de procesado/guardado: solo presentación + queries de lectura.
"""
import calendar
import unicodedata
import pandas as pd
import streamlit as st
from datetime import date

from src.db.db_manager import get_db_connection
from src.core.styles import TXT1, TXT2, TXT3

DIAS_ES = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES_ES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

_RUNNING_KW = {"running", "trail", "treadmill", "indoor_running", "street_running", "caminata"}
_DEFAULT_SPORT_EMOJI = "🏅"


# ---------------------------------------------------------------------------
# Helpers de texto / formato
# ---------------------------------------------------------------------------

def _normalizar_txt(txt):
    t = str(txt or "").strip().lower()
    if not t:
        return ""
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    return " ".join(t.split())


def _emoji_deporte(tipo_deporte):
    t = _normalizar_txt(tipo_deporte)
    if not t:
        return _DEFAULT_SPORT_EMOJI
    exactos = {
        "carrera": "🏃", "carrera en pista": "🏃", "carrera en cinta": "🏃",
        "trail running": "🏔️", "ultra run": "🏃", "caminar e interior": "🚶",
        "senderismo": "🥾", "ciclismo": "🚴", "ciclismo de montana": "🚵",
        "ciclismo en interior": "🚴", "natacion en piscina": "🏊",
        "natacion en aguas abiertas": "🏊", "paddle surf": "🏄",
        "remo e interior": "🚣", "kayak": "🛶", "fuerza": "🏋️", "cardio": "❤️",
        "hiit": "⚡", "yoga": "🧘", "pilates": "🤸", "eliptica": "🔄", "step": "🪜",
        "subida de pisos": "🏢", "esqui": "🎿", "tenis": "🎾", "padel": "🎾",
    }
    if t in exactos:
        return exactos[t]
    for patron, emoji in [
        ("trail", "🏔️"), ("ultra", "🏃"), ("run", "🏃"), ("running", "🏃"),
        ("treadmill", "🏃"), ("walk", "🚶"), ("caminar", "🚶"), ("sender", "🥾"),
        ("hike", "🥾"), ("ciclismo", "🚴"), ("cycling", "🚴"), ("bike", "🚴"),
        ("mountain", "🚵"), ("mtb", "🚵"), ("natacion", "🏊"), ("swim", "🏊"),
        ("paddle", "🏄"), ("surf", "🏄"), ("row", "🚣"), ("remo", "🚣"),
        ("kayak", "🛶"), ("strength", "🏋️"), ("fuerza", "🏋️"), ("cardio", "❤️"),
        ("hiit", "⚡"), ("yoga", "🧘"), ("pilates", "🤸"), ("elipt", "🔄"),
        ("ellipt", "🔄"), ("step", "🪜"), ("stair", "🏢"), ("esqui", "🎿"),
        ("ski", "🎿"), ("tenis", "🎾"), ("tennis", "🎾"), ("padel", "🎾"),
    ]:
        if patron in t:
            return emoji
    return _DEFAULT_SPORT_EMOJI


def _dia_del_mes(fecha_val, anio, mes):
    txt = str(fecha_val or "").strip()
    if not txt:
        return None
    try:
        dt = pd.to_datetime(txt, errors="coerce")
        if pd.isna(dt):
            return None
        if int(dt.year) == int(anio) and int(dt.month) == int(mes):
            return int(dt.day)
    except Exception:
        return None
    return None


def _safe_float(v):
    try:
        if pd.isna(v):
            return None
        return float(v)
    except Exception:
        return None


def _fmt_ritmo(ritmo):
    val = _safe_float(ritmo)
    if val is None or val <= 0:
        return None
    m = int(val)
    s = int(round((val - m) * 60))
    if s == 60:
        m += 1
        s = 0
    return f"{m}:{s:02d}/km"


def _fmt_bpm(fc):
    val = _safe_float(fc)
    if val is None or val <= 0:
        return None
    return f"{val:.0f} bpm"


def formato_fecha_larga(d):
    """Devuelve 'Viernes 11 de Abril'."""
    return f"{DIAS_ES[d.weekday()]} {d.day} de {MESES_ES[d.month - 1]}"


def chip_nota(nota):
    """Chip HTML coloreado según contenido de la nota."""
    if not nota or not str(nota).strip():
        return ""
    n = str(nota).lower()
    if any(k in n for k in ["subir", "genial", "bien", "perfecto"]):
        color, bg = "#4ade80", "#1a3a1a"
    elif any(k in n for k in ["no termino", "no terminó", "débil", "debil", "mal"]):
        color, bg = "#f87171", "#2a1a1a"
    else:
        color, bg = "#818cf8", "#1a1a2a"
    return (
        f'<span style="background:{bg};color:{color};padding:2px 7px;'
        f'border-radius:4px;font-size:10px">{nota}</span>'
    )


def ultimo_dia_con_actividad(dias_mes):
    if not dias_mes:
        return None
    return max(dias_mes.keys())


# ---------------------------------------------------------------------------
# Carga de actividad del mes (para calendario)
# ---------------------------------------------------------------------------

def cargar_dias_mes(usuario_id, anio, mes):
    """Devuelve {dia: {'tipo':'run|gym|both|sport','emoji':str}} para anio/mes."""
    uid_txt = str(usuario_id).strip()
    conn = get_db_connection()
    try:
        rows_f = conn.execute(
            "SELECT fecha, tipo_registro FROM sesiones_fuerza WHERE CAST(usuario_id AS TEXT)=?",
            (uid_txt,)).fetchall()
        rows_g = conn.execute(
            "SELECT fecha, tipo_deporte FROM actividades_garmin WHERE CAST(usuario_id AS TEXT)=?",
            (uid_txt,)).fetchall()
    except Exception:
        rows_f = rows_g = []
    finally:
        conn.close()

    dias: dict = {}
    for fecha_s, tipo_r in rows_f:
        d = _dia_del_mes(fecha_s, anio, mes)
        if d is None:
            continue
        tipo_r = (tipo_r or "").lower()
        if tipo_r in ("fuerza", "mixto", "general"):
            actual = dias.get(d)
            if actual and actual.get("tipo") in ("run", "sport"):
                sport_emoji = actual.get("emoji") or _DEFAULT_SPORT_EMOJI
                dias[d] = {"tipo": "both", "emoji": f"🏋️{sport_emoji}"}
            else:
                dias[d] = {"tipo": "gym", "emoji": "🏋️"}

    for fecha_s, tipo_d in rows_g:
        d = _dia_del_mes(fecha_s, anio, mes)
        if d is None:
            continue
        tipo_d = (tipo_d or "").lower()
        es_run = any(k in tipo_d for k in _RUNNING_KW)
        es_gym = any(k in tipo_d for k in ("strength", "fuerza"))
        emoji_dep = _emoji_deporte(tipo_d)
        actual = dias.get(d)
        if not actual:
            dias[d] = {"tipo": "gym" if es_gym else ("run" if es_run else "sport"),
                       "emoji": emoji_dep}
            continue
        tipo_actual = actual.get("tipo", "")
        if tipo_actual == "gym":
            if es_gym:
                if actual.get("emoji") in ("", _DEFAULT_SPORT_EMOJI):
                    actual["emoji"] = emoji_dep
            else:
                dias[d] = {"tipo": "both",
                           "emoji": f"🏋️{emoji_dep}"}
            continue
        if es_gym:
            dias[d] = {"tipo": "both",
                       "emoji": f"🏋️{actual.get('emoji') or _DEFAULT_SPORT_EMOJI}"}
            continue
        if tipo_actual == "sport" and es_run:
            actual["tipo"] = "run"
        if actual.get("emoji") in ("", _DEFAULT_SPORT_EMOJI) and emoji_dep:
            actual["emoji"] = emoji_dep
    return dias


# ---------------------------------------------------------------------------
# Calendario HTML con día seleccionado destacado
# ---------------------------------------------------------------------------

def html_calendario_con_seleccion(dias_mes, anio, mes, dia_sel=None):
    colores = {
        "run":   {"bg": "#1a3a1a", "border": "#a3e635", "txt": "#a3e635"},
        "gym":   {"bg": "#1e1b3a", "border": "#7c3aed", "txt": "#a78bfa"},
        "both":  {"bg": "#1a2a1a", "border": "#a3e635", "txt": "#a3e635"},
        "sport": {"bg": "#162338", "border": "#60a5fa", "txt": "#93c5fd"},
    }
    hoy = date.today()
    primer_dia, total_dias = calendar.monthrange(anio, mes)
    cabecera = "".join(
        f"<div style='text-align:center;font-size:10px;color:#484f58;"
        f"font-weight:600;padding-bottom:4px;'>{d}</div>"
        for d in ["L", "M", "X", "J", "V", "S", "D"])

    celdas = ["<div></div>"] * primer_dia
    for dia in range(1, total_dias + 1):
        info = dias_mes.get(dia, {})
        tipo = info.get("tipo", "") if isinstance(info, dict) else ""
        cfg = colores.get(tipo, {})
        bg = cfg.get("bg", "#0d1117")
        border = cfg.get("border", "#21262d")
        txt_color = cfg.get("txt", "#30363d")
        emoji = info.get("emoji", "") if isinstance(info, dict) else ""
        es_hoy = (anio == hoy.year and mes == hoy.month and dia == hoy.day)
        es_sel = (dia == dia_sel)
        bw = "1px" if not tipo else "2px"
        shadow = ""
        if es_hoy:
            shadow = "box-shadow:0 0 0 2px #a3e635;"
        if es_sel:
            shadow = "box-shadow:0 0 0 2.5px #f59e0b;"
        celdas.append(
            f"<div style='background:{bg};border:{bw} solid {border};border-radius:6px;"
            f"aspect-ratio:1;display:flex;flex-direction:column;align-items:center;"
            f"justify-content:center;position:relative;overflow:hidden;{shadow}'>"
            f"<div style='position:absolute;top:3px;right:5px;font-size:9px;"
            f"color:{txt_color};font-weight:700;line-height:1;'>{dia}</div>"
            f"<div style='font-size:18px;line-height:1;'>{emoji}</div>"
            f"</div>"
        )
    grid = "".join(celdas)
    return (
        "<div style='margin-top:6px;'>"
        f"<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:3px;"
        f"margin-bottom:3px;'>{cabecera}</div>"
        f"<div style='display:grid;grid-template-columns:repeat(7,1fr);gap:3px;'>{grid}</div>"
        "</div>"
    )


# ---------------------------------------------------------------------------
# Borrar sesión (reutilizado por render_sesiones_del_dia)
# ---------------------------------------------------------------------------

def borrar_sesion(usuario_id, sesion_id):
    try:
        sid = int(sesion_id)
    except Exception:
        return False, "ID inválido"
    uid_txt = str(usuario_id).strip()
    conn = get_db_connection()
    try:
        conn.execute(
            "DELETE FROM ejercicios_fuerza WHERE sesion_id IN ("
            "SELECT id FROM sesiones_fuerza WHERE id=? AND CAST(usuario_id AS TEXT)=?)",
            (sid, uid_txt))
        cur = conn.execute(
            "DELETE FROM sesiones_fuerza WHERE id=? AND CAST(usuario_id AS TEXT)=?",
            (sid, uid_txt))
        conn.commit()
        if getattr(cur, "rowcount", 1) == 0:
            return False, "Sin cambios"
        return True, "Sesión borrada"
    except Exception as e:
        return False, f"Error: {e}"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Render: Sesiones de un día
# ---------------------------------------------------------------------------

def render_sesiones_del_dia(usuario_id, fecha_dt):
    """Renderiza sesiones (fuerza + Garmin sin enlazar) de la fecha dada."""
    fecha_str = fecha_dt.strftime("%Y-%m-%d")
    conn = get_db_connection()
    try:
        df_f = pd.read_sql_query(
            "SELECT id, fecha, tipo_registro, resumen, actividad_garmin_id "
            "FROM sesiones_fuerza WHERE usuario_id=? AND fecha=? ORDER BY id ASC",
            conn, params=(usuario_id, fecha_str))
        df_g = pd.read_sql_query(
            "SELECT id_actividad, fecha, tipo_deporte, distancia_m, tiempo_seg, "
            "ritmo_medio, fc_media, cadencia_media "
            "FROM actividades_garmin WHERE usuario_id=? AND fecha=? "
            "ORDER BY id_actividad ASC",
            conn, params=(usuario_id, fecha_str))
    except Exception:
        df_f = pd.DataFrame()
        df_g = pd.DataFrame()

    ids_vinc = set()
    if not df_f.empty and "actividad_garmin_id" in df_f.columns:
        ids_vinc = {str(v) for v in df_f["actividad_garmin_id"].dropna().tolist()
                    if str(v).strip() not in ("", "None")}
    df_g_libre = df_g.copy()
    if not df_g_libre.empty and ids_vinc:
        df_g_libre = df_g_libre[~df_g_libre["id_actividad"].astype(str).isin(ids_vinc)]

    n_total = len(df_f) + len(df_g_libre)
    titulo = formato_fecha_larga(fecha_dt)

    # Mensaje de borrado tras rerun
    key_del_ok = f"del_ok_{usuario_id}"
    if key_del_ok in st.session_state:
        st.success(st.session_state.pop(key_del_ok))

    if n_total == 0:
        st.markdown(
            f"<div style='color:{TXT1};font-size:14px;font-weight:700;margin:0 0 6px;'>"
            f"{titulo}</div>"
            f"<div style='color:{TXT3};font-size:12px;'>Sin actividad registrada este día</div>",
            unsafe_allow_html=True)
        conn.close()
        return

    plural = "es" if n_total != 1 else ""
    st.markdown(
        f"<div style='color:{TXT1};font-size:14px;font-weight:700;margin:0 0 8px;'>"
        f"{titulo} · {n_total} sesión{plural} registrada{'s' if n_total != 1 else ''}</div>",
        unsafe_allow_html=True)

    primero = True
    for _, row in df_f.iterrows():
        _render_sesion_fuerza(conn, usuario_id, row, expanded=primero)
        primero = False
    for _, row in df_g_libre.iterrows():
        _render_sesion_garmin(row, expanded=primero)
        primero = False
    conn.close()


def _render_sesion_fuerza(conn, usuario_id, row, expanded):
    sesion_id = row.get("id")
    es_fuerza = (str(row.get("tipo_registro", "")).lower() == "fuerza")
    actividad_id = row.get("actividad_garmin_id")
    tipo_txt = str(row.get("tipo_registro", "")).capitalize()

    df_det = pd.DataFrame()
    df_garmin = pd.DataFrame()
    if es_fuerza and sesion_id is not None:
        try:
            df_det = pd.read_sql_query(
                "SELECT ejercicio, series, repeticiones, peso, sensaciones, grupo_muscular "
                "FROM ejercicios_fuerza WHERE sesion_id=?",
                conn, params=(int(sesion_id),))
        except Exception:
            pass
    if actividad_id not in (None, "", "None"):
        try:
            df_garmin = pd.read_sql_query(
                "SELECT distancia_m, tiempo_seg, ritmo_medio, fc_media, cadencia_media "
                "FROM actividades_garmin WHERE id_actividad=? LIMIT 1",
                conn, params=(actividad_id,))
        except Exception:
            pass

    icono = "🏋️" if es_fuerza else "🏃"
    if es_fuerza and not df_det.empty:
        n_ej = len(df_det)
        grupos = [g for g in df_det.get("grupo_muscular", pd.Series(dtype=str))
                  .dropna().astype(str).unique() if g]
        sub = f"{n_ej} ejercicios · {', '.join(grupos[:2]) if grupos else 'General'}"
        titulo = "Fuerza"
    elif not es_fuerza and not df_garmin.empty:
        g0 = df_garmin.iloc[0]
        km = (_safe_float(g0.get("distancia_m")) or 0) / 1000
        tmin = (_safe_float(g0.get("tiempo_seg")) or 0) / 60
        ritmo = _fmt_ritmo(g0.get("ritmo_medio")) or ""
        partes = [f"{km:.1f}km"]
        if tmin > 0:
            partes.append(f"{tmin:.0f}min")
        if ritmo:
            partes.append(ritmo)
        sub = " · ".join(partes)
        titulo = "Carrera"
    else:
        sub = str(row.get("resumen", "")) or tipo_txt
        titulo = tipo_txt or "Sesión"

    label = f"{icono}  {titulo} · {sub}"

    with st.expander(label, expanded=expanded):
        # Métricas en 3 columnas
        if es_fuerza and not df_det.empty:
            n_ej = len(df_det)
            grupos = [g for g in df_det.get("grupo_muscular", pd.Series(dtype=str))
                      .dropna().astype(str).unique() if g]
            c1, c2, c3 = st.columns(3)
            c1.metric("Ejercicios", n_ej)
            c2.metric("Grupos", len(grupos) or "—")
            c3.metric("Tipo", "Fuerza")
        elif not es_fuerza and not df_garmin.empty:
            g0 = df_garmin.iloc[0]
            km = (_safe_float(g0.get("distancia_m")) or 0) / 1000
            tmin = (_safe_float(g0.get("tiempo_seg")) or 0) / 60
            c1, c2, c3 = st.columns(3)
            c1.metric("Distancia", f"{km:.2f} km")
            c2.metric("Tiempo", f"{tmin:.0f} min" if tmin else "—")
            c3.metric("Ritmo", _fmt_ritmo(g0.get("ritmo_medio")) or "—")
            bpm = _fmt_bpm(g0.get("fc_media"))
            cad = _safe_float(g0.get("cadencia_media"))
            extras = []
            if bpm:
                extras.append(f"<span style='color:#f87171;'>❤ {bpm}</span>")
            if cad:
                extras.append(f"<span style='color:#22d3ee;'>👣 {cad:.0f} spm</span>")
            if extras:
                st.markdown(
                    f"<div style='display:flex;gap:14px;margin-top:6px;font-size:11px;'>"
                    f"{' · '.join(extras)}</div>",
                    unsafe_allow_html=True)

        # Tabla de ejercicios
        if es_fuerza and not df_det.empty:
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            cols_h = st.columns([2.6, 0.7, 0.7, 0.9, 2.0])
            for i, lbl in enumerate(["Ejercicio", "Series", "Reps", "Peso", "Notas"]):
                cols_h[i].markdown(
                    f"<div style='color:{TXT3};font-size:10px;font-weight:700;"
                    f"text-transform:uppercase;'>{lbl}</div>",
                    unsafe_allow_html=True)
            for _, ej in df_det.iterrows():
                fila = st.columns([2.6, 0.7, 0.7, 0.9, 2.0])
                fila[0].markdown(
                    f"<div style='font-size:12px;color:{TXT1};font-weight:500;'>"
                    f"{ej.get('ejercicio', '—')}</div>", unsafe_allow_html=True)
                fila[1].markdown(
                    f"<div style='font-size:12px;color:{TXT2};'>"
                    f"{ej.get('series', '—')}</div>", unsafe_allow_html=True)
                fila[2].markdown(
                    f"<div style='font-size:12px;color:{TXT2};'>"
                    f"{ej.get('repeticiones', '—')}</div>", unsafe_allow_html=True)
                peso = ej.get("peso", "—")
                peso_txt = f"{peso}kg" if peso not in ("—", None, "") else "—"
                fila[3].markdown(
                    f"<div style='font-size:12px;color:{TXT2};'>{peso_txt}</div>",
                    unsafe_allow_html=True)
                chip = chip_nota(ej.get("sensaciones", ""))
                fila[4].markdown(
                    chip or f"<span style='color:{TXT3};font-size:10px;'>—</span>",
                    unsafe_allow_html=True)

        # Línea Garmin enlazada
        if actividad_id not in (None, "", "None"):
            st.markdown(
                f"<div style='color:#60a5fa;font-size:11px;margin-top:10px;'>"
                f"⌚ Datos desde Garmin Connect</div>",
                unsafe_allow_html=True)

        _render_borrar(usuario_id, sesion_id, actividad_id)


def _render_sesion_garmin(row, expanded):
    """Carrera Garmin no enlazada a sesión de fuerza."""
    tipo = str(row.get("tipo_deporte", "Garmin") or "Garmin")
    km = (_safe_float(row.get("distancia_m")) or 0) / 1000
    tmin = (_safe_float(row.get("tiempo_seg")) or 0) / 60
    ritmo = _fmt_ritmo(row.get("ritmo_medio"))
    bpm = _fmt_bpm(row.get("fc_media"))
    cad = _safe_float(row.get("cadencia_media"))

    sub_partes = [f"{km:.1f}km"]
    if tmin:
        sub_partes.append(f"{tmin:.0f}min")
    if ritmo:
        sub_partes.append(ritmo)
    label = f"⌚  {tipo} · {' · '.join(sub_partes)}"

    with st.expander(label, expanded=expanded):
        c1, c2, c3 = st.columns(3)
        c1.metric("Distancia", f"{km:.2f} km")
        c2.metric("Tiempo", f"{tmin:.0f} min" if tmin else "—")
        c3.metric("Ritmo", ritmo or "—")
        extras = []
        if bpm:
            extras.append(f"<span style='color:#f87171;'>❤ {bpm}</span>")
        if cad:
            extras.append(f"<span style='color:#22d3ee;'>👣 {cad:.0f} spm</span>")
        if extras:
            st.markdown(
                f"<div style='display:flex;gap:14px;margin-top:6px;font-size:11px;'>"
                f"{' · '.join(extras)}</div>",
                unsafe_allow_html=True)
        st.markdown(
            f"<div style='color:#60a5fa;font-size:11px;margin-top:10px;'>"
            f"⌚ Datos desde Garmin Connect</div>",
            unsafe_allow_html=True)


def _render_borrar(usuario_id, sesion_id, actividad_id):
    if sesion_id is None:
        return
    tiene_garmin = actividad_id not in (None, "", "None")
    key_confirm = f"confirm_del_{sesion_id}"
    if key_confirm not in st.session_state:
        st.session_state[key_confirm] = False
    st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
    if not st.session_state[key_confirm]:
        if st.button(
            "🗑 Borrar sesión",
            key=f"del_{sesion_id}",
            help="Borra esta entrada del diario" + (" (Garmin se conserva)" if tiene_garmin else ""),
        ):
            st.session_state[key_confirm] = True
            st.rerun()
    else:
        st.warning("¿Borrar esta sesión?" + (" La actividad Garmin enlazada **no** se borrará." if tiene_garmin else ""))
        c_si, c_no = st.columns(2)
        with c_si:
            if st.button("Sí, borrar", key=f"si_{sesion_id}", type="primary"):
                ok, msg = borrar_sesion(usuario_id, sesion_id)
                st.session_state[key_confirm] = False
                if ok:
                    st.session_state[f"del_ok_{usuario_id}"] = msg
                else:
                    st.error(msg)
                st.rerun()
        with c_no:
            if st.button("Cancelar", key=f"no_{sesion_id}"):
                st.session_state[key_confirm] = False
                st.rerun()


# ---------------------------------------------------------------------------
# Render: Resultado de procesar nota
# ---------------------------------------------------------------------------

def render_resultado_procesado(usuario_id, sesiones_detectadas, on_guardar, on_descartar):
    n = len(sesiones_detectadas)
    plural = "es" if n > 1 else ""
    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='background:rgba(163,230,53,0.08);border:1px solid rgba(163,230,53,0.25);"
        f"border-radius:10px;padding:10px 12px;margin-bottom:10px;'>"
        f"<div style='color:#a3e635;font-size:13px;font-weight:700;'>"
        f"✅ {n} sesión{plural} detectada{'s' if n > 1 else ''}</div></div>",
        unsafe_allow_html=True)

    for i, ses in enumerate(sesiones_detectadas, 1):
        meta = ses["meta"]
        res = ses["res"]
        fecha_str = ses["fecha"].strftime("%d %b %Y")
        tipo_txt = meta["tipo"].capitalize()
        n_ej = len(res.get("datos", []))
        nota_estado = ses.get("nota_estado", "")
        vinc = ses.get("vinculo_running")
        with st.expander(
            f"📅 {fecha_str} · {tipo_txt} · {n_ej} ejercicio{'s' if n_ej != 1 else ''}",
            expanded=(i == 1),
        ):
            if nota_estado:
                st.markdown(
                    f"<div style='color:{TXT2};font-size:12px;margin-bottom:8px;'>"
                    f"💭 <i>{nota_estado}</i></div>",
                    unsafe_allow_html=True)
            if vinc:
                km = (_safe_float(vinc.get("distancia_m")) or 0) / 1000
                st.markdown(
                    f"<div style='color:#60a5fa;font-size:11px;margin-bottom:8px;'>"
                    f"⌚ Enlazado con Garmin · {km:.1f}km</div>",
                    unsafe_allow_html=True)
            if n_ej > 0 and res.get("datos"):
                cols_h = st.columns([2.6, 0.7, 0.7, 0.9, 1.6])
                for idx, lbl in enumerate(["Ejercicio", "Series", "Reps", "Peso", "Grupo"]):
                    cols_h[idx].markdown(
                        f"<div style='color:{TXT3};font-size:10px;font-weight:700;"
                        f"text-transform:uppercase;'>{lbl}</div>",
                        unsafe_allow_html=True)
                for ej in res["datos"]:
                    fila = st.columns([2.6, 0.7, 0.7, 0.9, 1.6])
                    fila[0].markdown(
                        f"<div style='font-size:12px;color:{TXT1};font-weight:500;'>"
                        f"{ej.get('ejercicio', '—')}</div>", unsafe_allow_html=True)
                    fila[1].markdown(
                        f"<div style='font-size:12px;color:{TXT2};'>"
                        f"{ej.get('series', '—')}</div>", unsafe_allow_html=True)
                    fila[2].markdown(
                        f"<div style='font-size:12px;color:{TXT2};'>"
                        f"{ej.get('repeticiones', '—')}</div>", unsafe_allow_html=True)
                    peso = ej.get("peso", "—")
                    fila[3].markdown(
                        f"<div style='font-size:12px;color:{TXT2};'>{peso}kg</div>"
                        if peso != "—" else f"<div style='color:{TXT3};font-size:11px;'>—</div>",
                        unsafe_allow_html=True)
                    fila[4].markdown(
                        f"<div style='color:{TXT3};font-size:10px;'>"
                        f"{ej.get('grupo_muscular', '—')}</div>",
                        unsafe_allow_html=True)
                    notas = ej.get("notas", "")
                    if notas:
                        st.markdown(
                            f"<div style='margin:4px 0 8px;color:{TXT3};"
                            f"font-size:10px;font-style:italic;'>📝 {notas}</div>",
                            unsafe_allow_html=True)

    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    c_g, c_d = st.columns([2, 1])
    with c_g:
        if st.button("💾 Guardar sesiones", use_container_width=True, type="primary",
                     key=f"btn_guardar_{usuario_id}"):
            on_guardar()
    with c_d:
        st.button("Descartar", use_container_width=True,
                  key=f"btn_descartar_{usuario_id}", on_click=on_descartar)

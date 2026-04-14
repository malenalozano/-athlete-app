"""
src/core/diario_tab_entreno.py — Tab "Entreno libre" del Diario.
Layout: dos columnas. Izq: textarea + resultado + lesiones. Der: historial + calendario.
"""

import calendar
import unicodedata
import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta
from typing import Optional

from src.db.db_manager import get_db_connection
from src.core.styles import ACCENT, CARD, BORDER, TXT1, TXT2, TXT3, label_upper, tipo_color
from src.core.ejercicios_helpers import buscar_ejercicio_id, guardar_historial
from src.core.ui_helpers_a import (
    _dividir_nota_por_fechas, _clasificar_segmento_diario, _extraer_nota_estado,
    _inferir_tipo_carrera, _buscar_actividad_running_fecha,
)
from src.core.ui_helpers_b import extraer_fecha_historica
from src.core.ai_coach import procesar_nota_fuerza

# Tipos de running para el calendario
_RUNNING_KW = {"running", "trail", "treadmill", "indoor_running", "street_running", "caminata"}
_DEFAULT_SPORT_EMOJI = "🏅"
MESES_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
            "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]


def _normalizar_txt(txt: str) -> str:
    t = str(txt or "").strip().lower()
    if not t:
        return ""
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    t = " ".join(t.split())
    return t


def _emoji_deporte(tipo_deporte: str) -> str:
    t = _normalizar_txt(tipo_deporte)
    if not t:
        return _DEFAULT_SPORT_EMOJI

    exactos = {
        "carrera": "🏃",
        "carrera en pista": "🏃",
        "carrera en cinta": "🏃",
        "trail running": "🏔️",
        "ultra run": "🏃",
        "caminar e interior": "🚶",
        "senderismo": "🥾",
        "ciclismo": "🚴",
        "ciclismo de montana": "🚵",
        "ciclismo en interior": "🚴",
        "natacion en piscina": "🏊",
        "natacion en aguas abiertas": "🏊",
        "paddle surf": "🏄",
        "remo e interior": "🚣",
        "kayak": "🛶",
        "fuerza": "🏋️",
        "cardio": "❤️",
        "hiit": "⚡",
        "yoga": "🧘",
        "pilates": "🤸",
        "eliptica": "🔄",
        "step": "🪜",
        "subida de pisos": "🏢",
        "esqui": "🎿",
        "tenis": "🎾",
        "padel": "🎾",
    }
    if t in exactos:
        return exactos[t]

    patrones = [
        ("trail", "🏔️"),
        ("ultra", "🏃"),
        ("run", "🏃"),
        ("running", "🏃"),
        ("treadmill", "🏃"),
        ("walk", "🚶"),
        ("caminar", "🚶"),
        ("sender", "🥾"),
        ("hike", "🥾"),
        ("ciclismo", "🚴"),
        ("cycling", "🚴"),
        ("bike", "🚴"),
        ("mountain", "🚵"),
        ("mtb", "🚵"),
        ("natacion", "🏊"),
        ("swim", "🏊"),
        ("paddle", "🏄"),
        ("surf", "🏄"),
        ("row", "🚣"),
        ("remo", "🚣"),
        ("kayak", "🛶"),
        ("strength", "🏋️"),
        ("fuerza", "🏋️"),
        ("cardio", "❤️"),
        ("hiit", "⚡"),
        ("yoga", "🧘"),
        ("pilates", "🤸"),
        ("elipt", "🔄"),
        ("ellipt", "🔄"),
        ("step", "🪜"),
        ("stair", "🏢"),
        ("esqui", "🎿"),
        ("ski", "🎿"),
        ("tenis", "🎾"),
        ("tennis", "🎾"),
        ("padel", "🎾"),
    ]
    for patron, emoji in patrones:
        if patron in t:
            return emoji

    return _DEFAULT_SPORT_EMOJI


def _dia_del_mes(fecha_val, anio: int, mes: int):
    """Devuelve el dia del mes si la fecha pertenece a anio/mes; si no, None."""
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


def _card_open() -> None:
    st.markdown(
        "<div style='background:#161b22;border:1px solid #21262d;border-radius:12px;padding:14px;margin-bottom:12px;'>",
        unsafe_allow_html=True,
    )


def _card_close() -> None:
    st.markdown("</div>", unsafe_allow_html=True)


def _color_nota(nota: str):
    if not nota:
        return None
    n = str(nota).lower()
    if any(k in n for k in ["subir", "genial", "bien", "perfecto", "excelente"]):
        return ("up", "#1a3a1a", "#4ade80")
    if any(k in n for k in ["no termino", "no terminó", "débil", "debil", "mal", "peor"]):
        return ("down", "#2a1a1a", "#f87171")
    return ("ok", "#1a1a2a", "#818cf8")


def _safe_float(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except Exception:
        return None


def _borrar_sesion_guardada(usuario_id: int, sesion_id) -> tuple[bool, str]:
    """Borra una sesion del diario validando que pertenezca al usuario activo."""
    try:
        sid = int(sesion_id)
    except Exception:
        return False, "ID de sesion invalido"

    uid_txt = str(usuario_id).strip()
    conn = get_db_connection()
    try:
        conn.execute(
            "DELETE FROM ejercicios_fuerza "
            "WHERE sesion_id IN ("
            "SELECT id FROM sesiones_fuerza WHERE id=? AND CAST(usuario_id AS TEXT)=?"
            ")",
            (sid, uid_txt),
        )
        cur = conn.execute(
            "DELETE FROM sesiones_fuerza WHERE id=? AND CAST(usuario_id AS TEXT)=?",
            (sid, uid_txt),
        )
        conn.commit()

        if getattr(cur, "rowcount", 1) == 0:
            return False, "No hubo cambios al intentar borrar"
        return True, "Sesion borrada"
    except Exception as e:
        return False, f"Error al borrar: {e}"
    finally:
        conn.close()


def _formatear_ritmo_min_km(ritmo_medio):
    valor = _safe_float(ritmo_medio)
    if valor is None or valor <= 0:
        return None
    minutos = int(valor)
    segundos = int(round((valor - minutos) * 60))
    if segundos == 60:
        minutos += 1
        segundos = 0
    return f"{minutos}:{segundos:02d} min/km"


def _formatear_bpm(fc_media):
    valor = _safe_float(fc_media)
    if valor is None or valor <= 0:
        return None
    return f"{valor:.0f}bpm"


# ---------------------------------------------------------------------------
# Calendario HTML
# ---------------------------------------------------------------------------

def _cargar_dias_mes(usuario_id: int, anio: int, mes: int) -> dict:
    """Devuelve {dia: {'tipo': 'run'|'gym'|'both'|'sport', 'emoji': str}}."""
    uid_txt = str(usuario_id).strip()
    conn = get_db_connection()
    try:
        # Cargar por usuario y filtrar mes en Python para tolerar formatos distintos de fecha.
        rows_f = conn.execute(
            "SELECT fecha, tipo_registro FROM sesiones_fuerza "
            "WHERE CAST(usuario_id AS TEXT)=?",
            (uid_txt,)).fetchall()
        rows_g = conn.execute(
            "SELECT fecha, tipo_deporte FROM actividades_garmin "
            "WHERE CAST(usuario_id AS TEXT)=?",
            (uid_txt,)).fetchall()
    except Exception:
        rows_f = rows_g = []
    finally:
        conn.close()

    dias: dict[int, dict] = {}

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
            dias[d] = {"tipo": "gym" if es_gym else ("run" if es_run else "sport"), "emoji": emoji_dep}
            continue

        tipo_actual = actual.get("tipo", "")
        if tipo_actual == "gym":
            if es_gym:
                if actual.get("emoji") in ("", _DEFAULT_SPORT_EMOJI):
                    actual["emoji"] = emoji_dep
            else:
                dias[d] = {"tipo": "both", "emoji": f"🏋️{emoji_dep}"}
            continue

        if es_gym:
            dias[d] = {"tipo": "both", "emoji": f"🏋️{actual.get('emoji') or _DEFAULT_SPORT_EMOJI}"}
            continue

        if tipo_actual == "sport" and es_run:
            actual["tipo"] = "run"

        if actual.get("emoji") in ("", _DEFAULT_SPORT_EMOJI) and emoji_dep:
            actual["emoji"] = emoji_dep

    return dias


def _render_calendario_interactivo(usuario_id: int, dias_mes: dict, anio: int, mes: int, _k_cal: str):
    """Renderiza solo el calendario visual HTML."""
    # Mostrar el HTML del calendario original (sin selectbox)
    st.markdown(
        html_calendario_entreno(dias_mes, anio, mes),
        unsafe_allow_html=True
    )
    return None


def _filtrar_sesiones_por_dia(df_hist: pd.DataFrame, fecha_str_formato: str, dia_seleccionado: Optional[int], anio: int, mes: int) -> pd.DataFrame:
    """Filtra sesiones por día seleccionado."""
    if dia_seleccionado is None:
        return df_hist
    
    # Construir la fecha en formato YYYY-MM-DD para el día seleccionado
    fecha_target = f"{anio:04d}-{mes:02d}-{dia_seleccionado:02d}"
    
    # Filtrar por fecha exacta
    return df_hist[df_hist["fecha"] == fecha_target]


def html_calendario_entreno(dias_mes: dict, anio: int, mes: int) -> str:
    colores = {
        "run":  {"bg": "#1a3a1a", "border": "#a3e635", "dot": "#a3e635", "emoji": "🏃"},
        "gym":  {"bg": "#1e1b3a", "border": "#818cf8", "dot": "#a78bfa", "emoji": "🏋️"},
        "both": {"bg": "#1a2a1a", "border": "#a3e635", "dot": "#a3e635", "emoji": "💪🏃"},
        "sport": {"bg": "#162338", "border": "#60a5fa", "dot": "#93c5fd", "emoji": _DEFAULT_SPORT_EMOJI},
    }
    hoy = date.today()
    primer_dia, total_dias = calendar.monthrange(anio, mes)
    # primer_dia: 0=lun … 6=dom

    cabecera_dias = ["L", "M", "X", "J", "V", "S", "D"]
    celdas_cab = "".join(
        f"<div style='text-align:center;font-size:10px;color:#484f58;"
        f"font-weight:600;padding-bottom:4px;'>{d}</div>"
        for d in cabecera_dias)

    celdas = []
    # Celdas vacías iniciales
    for _ in range(primer_dia):
        celdas.append("<div></div>")

    for dia in range(1, total_dias + 1):
        info = dias_mes.get(dia, {})
        tipo = info.get("tipo", "") if isinstance(info, dict) else str(info)
        cfg = colores.get(tipo, {})
        bg     = cfg.get("bg", "#161b22")
        border = cfg.get("border", "#21262d")
        emoji  = info.get("emoji", cfg.get("emoji", "")) if isinstance(info, dict) else cfg.get("emoji", "")
        es_hoy = (anio == hoy.year and mes == hoy.month and dia == hoy.day)
        border_hoy = f"border:2px solid #a3e635; box-shadow:0 0 0 2px #a3e63522;" if es_hoy else f"border:2px solid {border};"
        color_txt = cfg.get("dot", "#484f58") if tipo else "#484f58"
        font_w = "700" if tipo or es_hoy else "400"

        celdas.append(
            f"<div style='background:{bg};{border_hoy}border-radius:6px;"
            f"aspect-ratio:1;display:flex;flex-direction:column;"
            f"align-items:center;justify-content:center;position:relative;'>"
            f"<div style='font-size:11px;color:{'#a3e635' if es_hoy else color_txt};font-weight:{font_w};'>{dia}</div>"
            f"<div style='font-size:10px;line-height:1.1;margin-top:2px;'>{emoji}</div>"
            f"</div>"
        )

    grid = "".join(celdas)
    return f"""<div style='margin-top:8px;'>
  <div style='display:grid;grid-template-columns:repeat(7,1fr);gap:3px;margin-bottom:3px;'>
    {celdas_cab}
  </div>
  <div style='display:grid;grid-template-columns:repeat(7,1fr);gap:3px;'>
    {grid}
  </div>
  <div style='display:flex;gap:12px;margin-top:8px;flex-wrap:wrap;'>
    <span style='font-size:10px;color:#a3e635;'>🏃 Carrera</span>
    <span style='font-size:10px;color:#818cf8;'>🏋️ Fuerza</span>
    <span style='font-size:10px;color:#22d3ee;'>💪 Ambos</span>
        <span style='font-size:10px;color:#93c5fd;'>🏅 Otros deportes</span>
  </div>
</div>"""





# ---------------------------------------------------------------------------
# Tab principal
# ---------------------------------------------------------------------------

def render_tab_entreno(usuario_id: int):
    # CSS local para esta tab
    st.markdown("""<style>
div[data-testid="stTextArea"] textarea {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 10px !important;
    font-size: 13px !important;
    line-height: 1.6 !important;
}
div[data-testid="stTextArea"] textarea:focus {
    border-color: #a3e63560 !important;
    box-shadow: none !important;
}
</style>""", unsafe_allow_html=True)

    _k_res  = f"resultado_ia_{usuario_id}"
    _k_ses  = f"sesiones_detectadas_{usuario_id}"
    _k_cal  = f"cal_cursor_{usuario_id}"
    if _k_res not in st.session_state: st.session_state[_k_res] = None
    if _k_ses not in st.session_state: st.session_state[_k_ses] = []
    if _k_cal not in st.session_state:
        hoy = date.today()
        st.session_state[_k_cal] = (hoy.year, hoy.month)

    # Calculamos el mes/año y días disponibles ANTES de crear columnas
    anio_cal, mes_cal = st.session_state[_k_cal]
    dias_mes = _cargar_dias_mes(usuario_id, anio_cal, mes_cal)
    
    # Chequeamos si hay un día seleccionado en el selectbox
    sel_key = f"sel_dia_{usuario_id}_{anio_cal}_{mes_cal}"
    seleccion_actual = st.session_state.get(sel_key, "— Sin filtro —")
    hay_filtro_activo = seleccion_actual != "— Sin filtro —"
    
    # Si hay filtro activo, la columna izquierda se oculta
    if hay_filtro_activo:
        col_der = st.columns(1)[0]
    else:
        col_izq, col_der = st.columns([1, 1.8], gap="large")
        
        # ======================================================================
        # COLUMNA IZQUIERDA (solo si NO hay filtro activo)
        # ======================================================================
        with col_izq:

            # ── Sección 1: Textarea ─────────────────────────────────────────
            _card_open()
            st.markdown(label_upper("Entreno libre"), unsafe_allow_html=True)
            nota = st.text_area(
                "nota",
                height=150,
                key=f"nota_fuerza_{usuario_id}",
                placeholder=(
                    "Lunes\n"
                    "Hip Thrust 3x8 30kg - no he terminado la serie\n"
                    "Búlgaras 14kg  3x8 - me he sentido débil\n"
                ),
                label_visibility="hidden",
        )

        if nota.strip():
            fecha_auto, motivo = extraer_fecha_historica(nota)
            st.markdown(
                f"<div style='color:{TXT3};font-size:11px;margin:-4px 0 6px;'>"
                f"📅 Fecha detectada: <b style='color:{TXT2};'>"
                f"{fecha_auto.strftime('%d %b %Y')}</b> · {motivo}</div>",
                unsafe_allow_html=True)

        c_proc, c_hoy = st.columns([2, 1])
        with c_proc:
            procesar = st.button("⚡ Procesar nota", use_container_width=True, type="primary")
        with c_hoy:
            if st.button("Hoy", use_container_width=True):
                st.session_state["_fecha_override"] = date.today()

        if procesar and nota.strip():
            # Validar longitud de entrada
            if len(nota.strip()) > 5000:
                st.error(f"⚠️ Nota muy larga ({len(nota.strip())} caracteres). Máximo 5000.")
            else:
                sesiones_prep = []
                with st.spinner("Analizando…"):
                    for marca, frag in _dividir_nota_por_fechas(nota):
                        texto_seg   = frag if marca else nota
                        fecha_seg, _ = extraer_fecha_historica(texto_seg)
                        meta        = _clasificar_segmento_diario(texto_seg)
                        nota_estado = _extraer_nota_estado(texto_seg)
                        vinculo     = _buscar_actividad_running_fecha(usuario_id, fecha_seg)
                        res = (procesar_nota_fuerza(texto_seg, usuario_id=usuario_id)
                               if meta["has_fuerza"]
                               else {"exito": True, "datos": [], "raw": ""})
                        sesiones_prep.append({
                            "fecha": fecha_seg, "res": res, "texto": texto_seg,
                            "meta": meta, "nota_estado": nota_estado, "vinculo_running": vinculo,
                        })
                st.session_state[_k_ses] = sesiones_prep
                st.session_state[_k_res] = True
                st.rerun()

        _card_close()

        # ── Sección 2: Stats del mes ──────────────────────────────────────
        _card_open()
        anio_cal_temp, mes_cal_temp = st.session_state[_k_cal]
        dias_mes_temp = _cargar_dias_mes(usuario_id, anio_cal_temp, mes_cal_temp)
        st.markdown(label_upper("Stats del mes"), unsafe_allow_html=True)
        n_gym_temp = sum(1 for t in dias_mes_temp.values() if isinstance(t, dict) and t.get("tipo") in ("gym", "both"))
        n_run_temp = sum(1 for t in dias_mes_temp.values() if isinstance(t, dict) and t.get("tipo") in ("run", "both"))
        n_tot_temp = len(dias_mes_temp)
        st.markdown(
            f"<div style='display:flex;flex-direction:column;gap:12px;'>"
            f"<div style='background:rgba(163,230,53,0.08);border-radius:10px;padding:12px;text-align:center;'>"
            f"<div style='color:#a3e635;font-size:1.8rem;font-weight:800;'>{n_run_temp}</div>"
            f"<div style='color:#8B949E;font-size:0.72rem;font-weight:600;text-transform:uppercase;'>🏃 Carreras</div>"
            f"</div>"
            f"<div style='background:rgba(167,139,250,0.08);border-radius:10px;padding:12px;text-align:center;'>"
            f"<div style='color:#a78bfa;font-size:1.8rem;font-weight:800;'>{n_gym_temp}</div>"
            f"<div style='color:#8B949E;font-size:0.72rem;font-weight:600;text-transform:uppercase;'>🏋️ Fuerza</div>"
            f"</div>"
            f"<div style='background:rgba(201,255,0,0.06);border-radius:10px;padding:12px;text-align:center;'>"
            f"<div style='color:#C9FF00;font-size:1.8rem;font-weight:800;'>{n_tot_temp}</div>"
            f"<div style='color:#8B949E;font-size:0.72rem;font-weight:600;text-transform:uppercase;'>📅 Días</div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True)
        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        # Leyenda
        st.markdown(
            f"<div style='color:{TXT3};font-size:9px;'>"
            f"<div style='display:flex;align-items:center;gap:5px;margin-bottom:4px;'><span style='width:7px;height:7px;border-radius:50%;background:#a3e635;display:inline-block;'></span>Carrera</div>"
            f"<div style='display:flex;align-items:center;gap:5px;margin-bottom:4px;'><span style='width:7px;height:7px;border-radius:50%;background:#a78bfa;display:inline-block;'></span>Fuerza</div>"
            f"<div style='display:flex;align-items:center;gap:5px;'><span style='width:7px;height:7px;border-radius:50%;background:#60a5fa;display:inline-block;'></span>Ambos</div>"
            f"</div>",
            unsafe_allow_html=True)
        _card_close()

    # ======================================================================
    # COLUMNA DERECHA
    # ======================================================================
    with col_der:
        # ── Sección 3: Calendario (todo el ancho) ──────────────────────────
        anio_cal, mes_cal = st.session_state[_k_cal]
        dias_mes = _cargar_dias_mes(usuario_id, anio_cal, mes_cal)

        _card_open()
        st.markdown(label_upper("Calendario del mes"), unsafe_allow_html=True)

        nav_l, nav_c, nav_r = st.columns([1, 4, 1])
        with nav_l:
            if st.button("◀", key=f"cal_prev_{usuario_id}"):
                m, y = mes_cal - 1, anio_cal
                if m < 1: m, y = 12, y - 1
                st.session_state[_k_cal] = (y, m)
                st.rerun()
        with nav_c:
            st.markdown(
                f"<div style='text-align:center;font-size:13px;font-weight:700;"
                f"color:{TXT1};padding:4px 0;'>"
                f"{MESES_ES[mes_cal-1]} {anio_cal}</div>",
                unsafe_allow_html=True)
        with nav_r:
            if st.button("▶", key=f"cal_next_{usuario_id}"):
                m, y = mes_cal + 1, anio_cal
                if m > 12: m, y = 1, y + 1
                st.session_state[_k_cal] = (y, m)
                st.rerun()

        # Renderizar calendario interactivo
        dia_sel = _render_calendario_interactivo(usuario_id, dias_mes, anio_cal, mes_cal, _k_cal)
        _card_close()

        # ── Sección 4: Sesiones guardadas ──────────────────────────────
        _card_open()
        
        # SELECTBOX para filtrar por día - AQUÍ y no en el calendario
        if dias_mes:
            st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
            dias_ordenados = sorted(dias_mes.keys())
            opciones_display = ["— Sin filtro —"] + [f"{d:02d}" for d in dias_ordenados]
            
            col_sel, col_clear = st.columns([3, 1])
            with col_sel:
                seleccion = st.selectbox(
                    "Filtrar por día:",
                    options=opciones_display,
                    key=f"sel_dia_{usuario_id}_{anio_cal}_{mes_cal}",
                    label_visibility="collapsed"
                )
                dia_sel = None if seleccion == "— Sin filtro —" else int(seleccion)
            
            with col_clear:
                if st.button("✕", key=f"clear_sel_{usuario_id}_{anio_cal}_{mes_cal}", help="Limpiar filtro"):
                    st.session_state[f"sel_dia_{usuario_id}_{anio_cal}_{mes_cal}"] = "— Sin filtro —"
                    st.rerun()
        else:
            dia_sel = None
        
        # Mostrar el día seleccionado si existe
        if dia_sel:
            fecha_sel_str = f"{anio_cal:04d}-{mes_cal:02d}-{dia_sel:02d}"
            st.markdown(
                f"<div style='background:#1a2a1a;border:1px solid #30363d;border-radius:8px;padding:8px 12px;margin-bottom:12px;'>"
                f"<div style='color:{TXT2};font-size:12px;'>📅 Mostrando sesiones del <b>{dia_sel} de {MESES_ES[mes_cal-1]}</b></div>"
                f"</div>",
                unsafe_allow_html=True
            )
        else:
            st.markdown(label_upper("Sesiones guardadas"), unsafe_allow_html=True)
        
        key_del_ok = f"del_ok_{usuario_id}"
        if key_del_ok in st.session_state:
            st.success(st.session_state.pop(key_del_ok))
        conn = get_db_connection()
        try:
            df_hist = pd.read_sql_query(
                "SELECT id, fecha, tipo_registro, resumen, actividad_garmin_id FROM sesiones_fuerza "
                "WHERE usuario_id=? ORDER BY fecha DESC LIMIT 10",
                conn, params=(usuario_id,))
            df_garmin = pd.read_sql_query(
                "SELECT id_actividad, fecha, tipo_deporte, distancia_m, tiempo_seg, ritmo_medio, fc_media, cadencia_media "
                "FROM actividades_garmin WHERE usuario_id=? ORDER BY fecha DESC LIMIT 20",
                conn, params=(usuario_id,))
        except Exception:
            df_hist = pd.DataFrame()
            df_garmin = pd.DataFrame()

        # Aplicar filtro de día si está seleccionado
        if dia_sel:
            fecha_sel_str = f"{anio_cal:04d}-{mes_cal:02d}-{dia_sel:02d}"
            df_hist = df_hist[df_hist["fecha"] == fecha_sel_str]
            df_garmin = df_garmin[df_garmin["fecha"] == fecha_sel_str]

        actividad_ids_vinculadas = set()
        if not df_hist.empty and "actividad_garmin_id" in df_hist.columns:
            actividad_ids_vinculadas = set(
                int(v) for v in df_hist["actividad_garmin_id"].dropna().tolist() if str(v).strip() not in ("", "None")
            )

        df_garmin_libre = df_garmin.copy()
        if not df_garmin_libre.empty and "id_actividad" in df_garmin_libre.columns and actividad_ids_vinculadas:
            df_garmin_libre = df_garmin_libre[~df_garmin_libre["id_actividad"].isin(actividad_ids_vinculadas)]

        if df_hist.empty and df_garmin_libre.empty:
            if dia_sel:
                st.markdown(
                    f"<div style='text-align:center;padding:32px 16px;'>"
                    f"<div style='font-size:28px;margin-bottom:8px;'>📅</div>"
                    f"<div style='color:{TXT2};font-size:13px;font-weight:500;'>"
                    f"Sin sesiones el {dia_sel} de {MESES_ES[mes_cal-1]}</div>"
                    f"<div style='color:{TXT3};font-size:11px;margin-top:4px;'>"
                    f"Selecciona otro día o añade un entrenamiento</div>"
                    f"</div>",
                    unsafe_allow_html=True)
            else:
                st.markdown(
                    f"<div style='text-align:center;padding:32px 16px;'>"
                    f"<div style='font-size:28px;margin-bottom:8px;'>📋</div>"
                    f"<div style='color:{TXT2};font-size:13px;font-weight:500;'>"
                    f"Sin sesiones guardadas</div>"
                    f"<div style='color:{TXT3};font-size:11px;margin-top:4px;'>"
                    f"Escribe tu entrenamiento y pulsa ⚡ Procesar</div>"
                    f"</div>",
                    unsafe_allow_html=True)
        else:
            for idx, row in df_hist.iterrows():
                tc       = tipo_color(row.get("tipo_registro", ""))
                tipo_txt = str(row.get("tipo_registro", "")).capitalize()
                resumen  = str(row.get("resumen", ""))
                fecha_d  = str(row.get("fecha", ""))
                es_fuerza = (str(row.get("tipo_registro", "")).lower() == "fuerza")
                badge_bg = "#1e1b3a" if es_fuerza else "#1a3a1a"
                badge_fg = "#a78bfa" if es_fuerza else "#a3e635"
                actividad_id = row.get("actividad_garmin_id")
                df_det = pd.DataFrame()
                df_garmin = pd.DataFrame()
                if es_fuerza and row.get("id") is not None:
                    try:
                        df_det = pd.read_sql_query(
                            "SELECT ejercicio, series, repeticiones, peso, sensaciones, grupo_muscular FROM ejercicios_fuerza WHERE sesion_id=?",
                            conn,
                            params=(int(row.get("id")),),
                        )
                    except Exception:
                        df_det = pd.DataFrame()
                elif actividad_id is not None:
                    try:
                        df_garmin = pd.read_sql_query(
                            "SELECT distancia_m, tiempo_seg, ritmo_medio, fc_media FROM actividades_garmin WHERE id_actividad=? LIMIT 1",
                            conn,
                            params=(actividad_id,),
                        )
                    except Exception:
                        df_garmin = pd.DataFrame()

                if es_fuerza and not df_det.empty:
                    grupos = [g for g in df_det.get("grupo_muscular", pd.Series(dtype=str)).dropna().astype(str).unique().tolist() if g]
                    titulo = f"{len(df_det)} ejercicios · {', '.join(grupos[:2]) if grupos else 'General'}"
                elif not es_fuerza and not df_garmin.empty:
                    km = float(df_garmin.iloc[0].get("distancia_m", 0) or 0) / 1000
                    titulo = f"Carrera Z2 · {km:.1f}km"
                elif not es_fuerza:
                    titulo = resumen or "Carrera"
                else:
                    titulo = resumen or f"{len(df_det)} ejercicios"

                with st.expander(f"• {titulo} · {fecha_d} · {tipo_txt}", expanded=False):
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px;'>"
                        f"<span style='width:8px;height:8px;border-radius:50%;background:{tc};display:inline-block;'></span>"
                        f"<div style='flex:1;min-width:0;'>"
                        f"<div style='color:{TXT1};font-size:13px;font-weight:600;line-height:1.2;'>{titulo}</div>"
                        f"<div style='color:{TXT3};font-size:10px;margin-top:2px;'>{fecha_d} · {tipo_txt}</div>"
                        f"</div>"
                        f"<span style='background:{badge_bg};color:{badge_fg};border-radius:999px;padding:2px 8px;"
                        f"font-size:10px;font-weight:700;'>" + ("Fuerza" if es_fuerza else "Carrera") + "</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )

                    if es_fuerza and not df_det.empty:
                        st.markdown(
                            f"<div style='margin-bottom:6px;color:{TXT2};font-size:11px;font-weight:600;'>"
                            f"{len(df_det)} ejercicio{'s' if len(df_det) != 1 else ''} · "
                            f"{', '.join(sorted(set(str(x) for x in df_det['ejercicio'].dropna().tolist()))[:3])}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        cols_tbl = st.columns([3, 0.8, 0.8, 1, 1.4])
                        with cols_tbl[0]:
                            st.caption("Ejercicio")
                        with cols_tbl[1]:
                            st.caption("Series")
                        with cols_tbl[2]:
                            st.caption("Reps")
                        with cols_tbl[3]:
                            st.caption("Peso")
                        with cols_tbl[4]:
                            st.caption("Notas")
                        for _, ej in df_det.iterrows():
                            nota = str(ej.get("sensaciones", "") or "")
                            chip = _color_nota(nota)
                            if chip:
                                _, bg_chip, fg_chip = chip
                                chip_html = f"<span style='background:{bg_chip};color:{fg_chip};border-radius:999px;padding:2px 8px;font-size:10px;font-weight:600;'>" \
                                            f"{nota if nota else '—'}" \
                                            f"</span>"
                            else:
                                chip_html = f"<span style='color:{TXT3};font-size:10px;'>—</span>"
                            fila_cols = st.columns([3, 0.8, 0.8, 1, 1.4])
                            fila_cols[0].markdown(f"<div style='font-size:12px;color:{TXT1};'>{ej.get('ejercicio','—')}</div>", unsafe_allow_html=True)
                            fila_cols[1].markdown(f"<div style='font-size:12px;color:{TXT2};'>{ej.get('series','—')}</div>", unsafe_allow_html=True)
                            fila_cols[2].markdown(f"<div style='font-size:12px;color:{TXT2};'>{ej.get('repeticiones','—')}</div>", unsafe_allow_html=True)
                            fila_cols[3].markdown(f"<div style='font-size:12px;color:{TXT2};'>{ej.get('peso','—')}</div>", unsafe_allow_html=True)
                            fila_cols[4].markdown(chip_html, unsafe_allow_html=True)
                    if not es_fuerza and not df_garmin.empty:
                        g = df_garmin.iloc[0]
                        km = (_safe_float(g.get("distancia_m")) or 0) / 1000
                        ritmo_txt = _formatear_ritmo_min_km(g.get("ritmo_medio"))
                        bpm_txt = _formatear_bpm(g.get("fc_media"))
                        partes = [f"⌚ Enlazado con Garmin · {km:.1f}km"]
                        if ritmo_txt:
                            partes.append(ritmo_txt)
                        if bpm_txt:
                            partes.append(bpm_txt)
                        st.markdown(
                            f"<div style='color:#60a5fa;font-size:11px;margin:4px 0 8px;'>"
                            f"{' · '.join(partes)}</div>",
                            unsafe_allow_html=True,
                        )

                    # ── Botón borrar ────────────────────────────────────
                    sesion_id_val = row.get("id")
                    tiene_garmin  = actividad_id not in (None, "", "None")
                    key_confirm   = f"confirm_del_{sesion_id_val}"
                    if key_confirm not in st.session_state:
                        st.session_state[key_confirm] = False

                    st.markdown("<div style='margin-top:8px;'></div>", unsafe_allow_html=True)
                    if not st.session_state[key_confirm]:
                        if st.button("🗑 Borrar sesión", key=f"del_{sesion_id_val}",
                                     help="Borra esta entrada del diario" + (" (la actividad Garmin se conserva)" if tiene_garmin else "")):
                            st.session_state[key_confirm] = True
                            st.rerun()
                    else:
                        aviso = "¿Borrar esta sesión? La actividad Garmin enlazada **no** se borrará." if tiene_garmin else "¿Borrar esta sesión?"
                        st.warning(aviso)
                        col_si, col_no = st.columns(2)
                        with col_si:
                            if st.button("Sí, borrar", key=f"confirm_si_{sesion_id_val}", type="primary"):
                                ok_del, msg_del = _borrar_sesion_guardada(usuario_id, sesion_id_val)
                                st.session_state[key_confirm] = False
                                if not ok_del:
                                    st.error(msg_del)
                                else:
                                    st.session_state[f"del_ok_{usuario_id}"] = "Sesión borrada"
                                st.rerun()
                        with col_no:
                            if st.button("Cancelar", key=f"confirm_no_{sesion_id_val}"):
                                st.session_state[key_confirm] = False
                                st.rerun()

        if not df_garmin_libre.empty:
            st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
            st.markdown(label_upper("Actividades Garmin"), unsafe_allow_html=True)
            for _, row in df_garmin_libre.iterrows():
                tipo_deporte = str(row.get("tipo_deporte", "") or "Garmin")
                fecha_d = str(row.get("fecha", ""))
                km = (_safe_float(row.get("distancia_m")) or 0) / 1000
                ritmo_txt = _formatear_ritmo_min_km(row.get("ritmo_medio"))
                bpm_txt = _formatear_bpm(row.get("fc_media"))
                cadencia_val = _safe_float(row.get('cadencia_media'))
                cadencia_txt = f"{cadencia_val:.0f} spm" if cadencia_val is not None else None
                subtitulo = [f"⌚ Garmin · {km:.1f}km"]
                if ritmo_txt:
                    subtitulo.append(ritmo_txt)
                if bpm_txt:
                    subtitulo.append(bpm_txt)
                if cadencia_txt:
                    subtitulo.append(cadencia_txt)

                with st.expander(f"• {tipo_deporte} · {fecha_d}", expanded=False):
                    st.markdown(
                        f"<div style='display:flex;align-items:center;gap:10px;margin-bottom:6px;'>"
                        f"<span style='width:8px;height:8px;border-radius:50%;background:#60a5fa;display:inline-block;'></span>"
                        f"<div style='flex:1;min-width:0;'>"
                        f"<div style='color:{TXT1};font-size:13px;font-weight:600;line-height:1.2;'>{tipo_deporte}</div>"
                        f"<div style='color:{TXT3};font-size:10px;margin-top:2px;'>{fecha_d} · Garmin</div>"
                        f"</div>"
                        f"<span style='background:#17335c;color:#93c5fd;border-radius:999px;padding:2px 8px;"
                        f"font-size:10px;font-weight:700;'>Garmin</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div style='color:#60a5fa;font-size:11px;margin:4px 0 8px;'>"
                        f"{' · '.join(subtitulo)}</div>",
                        unsafe_allow_html=True,
                    )

        conn.close()
        _card_close()


# ---------------------------------------------------------------------------
# Guardar sesiones en BD
# ---------------------------------------------------------------------------

def _guardar_sesiones(usuario_id: int, sesiones: list):
    conn = get_db_connection()
    try:
        for ses in sesiones:
            meta  = ses["meta"]
            vinc  = ses["vinculo_running"]
            res_s = ses["res"]
            tipo_reg = meta["tipo"]
            if tipo_reg == "carrera":
                resumen = f"Carrera · {_inferir_tipo_carrera(ses['texto'])}"
            elif res_s["datos"]:
                grupos = list({
                    str(e.get("grupo_muscular","")).strip()
                    for e in res_s["datos"] if e.get("grupo_muscular")
                })
                resumen = f"{len(res_s['datos'])} ejercicios · {', '.join(grupos) or 'General'}"
            else:
                resumen = "Nota de entrenamiento"

            cur = conn.cursor()
            cur.execute(
                "INSERT INTO sesiones_fuerza "
                "(usuario_id,fecha,nota_original,resumen,created_at,"
                "tipo_registro,actividad_garmin_id,nota_estado,lesion_flag) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (usuario_id, ses["fecha"].strftime("%Y-%m-%d"), ses["texto"], resumen,
                 datetime.now().strftime("%Y-%m-%d %H:%M:%S"), tipo_reg,
                 vinc["id_actividad"] if vinc else None,
                 ses["nota_estado"], 1 if meta["has_lesion"] else 0))
            sesion_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
            fecha_str = ses["fecha"].strftime("%Y-%m-%d")

            for ej in res_s["datos"]:
                conn.execute(
                    "INSERT INTO ejercicios_fuerza "
                    "(sesion_id,ejercicio,peso,series,repeticiones,"
                    "grupo_muscular,musculo_principal,rpe,sensaciones) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    (sesion_id, ej.get("ejercicio",""),
                     float(ej.get("peso",0) or 0),
                     int(ej.get("series",0) or 0),
                     int(ej.get("repeticiones",0) or 0),
                     ej.get("grupo_muscular","Tren Inferior"),
                     ej.get("musculo_principal","Varios"),
                     int(ej.get("rpe",5) or 5),
                     ej.get("notas","")))
                ej_id = buscar_ejercicio_id(usuario_id, ej.get("ejercicio",""))
                
                # Si no existe en biblioteca, crear automáticamente
                if not ej_id:
                    nombre_ej = ej.get("ejercicio","").strip()
                    if nombre_ej:
                        try:
                            conn.execute(
                                "INSERT INTO ejercicios_biblioteca "
                                "(usuario_id,nombre,grupo_muscular,musculo_principal,tipo,activo,creado_en) "
                                "VALUES (?,?,?,?,?,1,?)",
                                (usuario_id, nombre_ej,
                                 ej.get("grupo_muscular","Tren Inferior"),
                                 ej.get("musculo_principal","Varios"),
                                 "Fuerza",
                                 datetime.now().strftime("%Y-%m-%d")))
                            ej_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        except Exception:
                            pass
                
                if ej_id:
                    guardar_historial(
                        usuario_id, ej_id, fecha_str,
                        float(ej.get("peso",0) or 0),
                        int(ej.get("series",0) or 1),
                        int(ej.get("repeticiones",0) or 1),
                        int(ej.get("rpe",6) or 6),
                        str(ej.get("notas","") or ""))

        conn.commit()
        st.cache_data.clear()
        n = len(sesiones)
        st.success(f"✅ {n} sesión{'es' if n>1 else ''} guardada{'s' if n>1 else ''}")
        st.session_state[f"resultado_ia_{usuario_id}"] = None
        st.session_state[f"sesiones_detectadas_{usuario_id}"] = []
        st.rerun()
    except Exception as e:
        st.error(f"Error SQL: {e}")
    finally:
        conn.close()

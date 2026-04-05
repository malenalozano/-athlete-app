"""
src/core/diario_tab_entreno.py — Tab "Entreno libre" del Diario.
Layout: dos columnas. Izq: textarea + resultado + lesiones. Der: historial + calendario.
"""

import calendar
import pandas as pd
import streamlit as st
from datetime import datetime, date, timedelta

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


# ---------------------------------------------------------------------------
# Calendario HTML
# ---------------------------------------------------------------------------

def _cargar_dias_mes(usuario_id: int, anio: int, mes: int) -> dict:
    """Devuelve {dia: tipo} donde tipo ∈ 'run','gym','both','rest'."""
    mes_str = f"{anio:04d}-{mes:02d}"
    conn = get_db_connection()
    try:
        # Sesiones de fuerza del mes
        rows_f = conn.execute(
            "SELECT fecha, tipo_registro FROM sesiones_fuerza "
            "WHERE usuario_id=? AND fecha LIKE ?",
            (usuario_id, f"{mes_str}%")).fetchall()
        # Actividades Garmin del mes
        rows_g = conn.execute(
            "SELECT fecha, tipo_deporte FROM actividades_garmin "
            "WHERE usuario_id=? AND fecha LIKE ?",
            (usuario_id, f"{mes_str}%")).fetchall()
    except Exception:
        rows_f = rows_g = []
    finally:
        conn.close()

    dias: dict[int, str] = {}

    for fecha_s, tipo_r in rows_f:
        try:
            d = int(fecha_s[8:10])
        except Exception:
            continue
        tipo_r = (tipo_r or "").lower()
        if tipo_r in ("fuerza", "mixto", "general"):
            dias[d] = "both" if dias.get(d) == "run" else "gym"

    for fecha_s, tipo_d in rows_g:
        try:
            d = int(fecha_s[8:10])
        except Exception:
            continue
        tipo_d = (tipo_d or "").lower()
        es_run = any(k in tipo_d for k in _RUNNING_KW)
        if es_run:
            actual = dias.get(d)
            dias[d] = "both" if actual == "gym" else "run"

    return dias


def html_calendario_entreno(dias_mes: dict, anio: int, mes: int) -> str:
    colores = {
        "run":  {"bg": "#0e2a0e", "border": "#a3e63560", "dot": "#a3e635", "emoji": "🏃"},
        "gym":  {"bg": "#16164a", "border": "#818cf860", "dot": "#818cf8", "emoji": "🏋️"},
        "both": {"bg": "#0e221e", "border": "#22d3ee60", "dot": "#22d3ee", "emoji": "💪"},
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
        tipo = dias_mes.get(dia, "")
        cfg = colores.get(tipo, {})
        bg     = cfg.get("bg", "#0d1117")
        border = cfg.get("border", "#21262d")
        emoji  = cfg.get("emoji", "")
        es_hoy = (anio == hoy.year and mes == hoy.month and dia == hoy.day)
        border_hoy = f"border:2px solid {ACCENT};" if es_hoy else f"border:1px solid {border};"

        celdas.append(
            f"<div style='background:{bg};{border_hoy}border-radius:6px;"
            f"aspect-ratio:1;display:flex;flex-direction:column;"
            f"align-items:center;justify-content:center;position:relative;'>"
            f"<div style='font-size:11px;color:{'#a3e635' if es_hoy else TXT2};font-weight:{'700' if es_hoy else '400'};'>{dia}</div>"
            f"<div style='font-size:8px;line-height:1;'>{emoji}</div>"
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
  </div>
</div>"""


# ---------------------------------------------------------------------------
# Lesiones inline
# ---------------------------------------------------------------------------

_TIPOS_LESION = [
    "Periostitis", "Tendón de Aquiles", "Fascitis Plantar",
    "Rodilla inflamada", "Dolor de espalda", "Poleas (Dedos)",
    "Hombro inflamado", "Dolor de Cadera",
]
_GRADO_COLOR = {1: ("#22c55e", "Leve"), 2: ("#f59e0b", "Moderada"), 3: ("#ef4444", "Grave")}


def _render_lesiones_inline(usuario_id: int):
    st.markdown(
        f"<p style='color:{TXT3};font-size:10px;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:0.8px;margin:16px 0 6px;'>🦵 Lesiones activas</p>",
        unsafe_allow_html=True)

    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            "SELECT id, tipo, grado, fecha_inicio, notas FROM lesiones "
            "WHERE usuario_id=? AND activa=1 ORDER BY grado DESC, fecha_inicio",
            conn, params=(usuario_id,))
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()

    if df.empty:
        st.success("✓ Sin lesiones activas. ¡Sigue así!")
    else:
        for _, row in df.iterrows():
            g = max(1, min(3, int(row["grado"] or 1)))
            col_c, lbl = _GRADO_COLOR.get(g, ("#8b949e", "?"))
            try:
                dias = (date.today() - pd.to_datetime(row["fecha_inicio"]).date()).days
            except Exception:
                dias = "?"
            ci, cb = st.columns([5, 1])
            with ci:
                st.markdown(
                    f"<div style='background:{col_c}10;border-left:3px solid {col_c};"
                    f"border-radius:0 8px 8px 0;padding:8px 12px;margin-bottom:4px;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;'>"
                    f"<span style='font-weight:600;color:{TXT1};font-size:12px;'>{row['tipo']}</span>"
                    f"<span style='background:{col_c}22;color:{col_c};border-radius:999px;"
                    f"padding:1px 7px;font-size:10px;'>Grado {g} — {lbl}</span>"
                    f"<span style='color:{TXT3};font-size:10px;'>Día {dias}</span>"
                    f"</div></div>",
                    unsafe_allow_html=True)
            with cb:
                if st.button("✓ Ok", key=f"les_ok_{row['id']}"):
                    c2 = get_db_connection()
                    c2.execute("UPDATE lesiones SET activa=0, fecha_fin=? WHERE id=?",
                               (date.today().strftime("%Y-%m-%d"), row["id"]))
                    c2.commit(); c2.close(); st.rerun()

    with st.expander("+ Registrar lesión"):
        with st.form("form_lesion_inline", clear_on_submit=True):
            tipo_s = st.selectbox("Zona / Tipo", _TIPOS_LESION)
            grado_s = st.select_slider(
                "Grado",
                options=[1, 2, 3], value=1,
                format_func=lambda x: {1: "1 — Leve", 2: "2 — Moderada", 3: "3 — Grave"}[x])
            c1, c2 = st.columns(2)
            with c1:
                f_ini = st.date_input("Fecha inicio", value=date.today())
            with c2:
                notas_s = st.text_input("Notas", placeholder="Aparece al bajar escaleras…")
            if st.form_submit_button("Registrar", type="primary", use_container_width=True):
                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO lesiones (usuario_id,tipo,grado,fecha_inicio,activa,notas) "
                    "VALUES (?,?,?,?,1,?)",
                    (usuario_id, tipo_s, grado_s, str(f_ini), notas_s.strip() or None))
                conn.commit(); conn.close()
                st.success(f"'{tipo_s}' registrada."); st.rerun()


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

    if "resultado_ia"       not in st.session_state: st.session_state.resultado_ia       = None
    if "sesiones_detectadas" not in st.session_state: st.session_state.sesiones_detectadas = []
    if "cal_cursor"          not in st.session_state:
        hoy = date.today()
        st.session_state.cal_cursor = (hoy.year, hoy.month)

    col_izq, col_der = st.columns([1, 1], gap="large")

    # ======================================================================
    # COLUMNA IZQUIERDA
    # ======================================================================
    with col_izq:

        # ── Sección 1: Textarea ─────────────────────────────────────────
        st.markdown(label_upper("Entreno libre"), unsafe_allow_html=True)
        nota = st.text_area(
            "nota",
            height=150,
            key="nota_fuerza",
            placeholder=(
                "Lunes\n"
                "Hip Thrust 3x8 30kg  no he terminado la serie\n"
                "Búlgaras 14kg  3x8  me he sentido débil\n\n"
                "Martes\n"
                "Dominadas 3x6  no termino\n"
                "Remo abierto 3x8 27kg\n"
                "Bíceps Martillo  3x8 22kg"
            ),
            label_visibility="collapsed",
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
            st.session_state.sesiones_detectadas = sesiones_prep
            st.session_state.resultado_ia = True
            st.rerun()

        # ── Sección 2: Resultado ────────────────────────────────────────
        if st.session_state.resultado_ia and st.session_state.sesiones_detectadas:
            for ses in st.session_state.sesiones_detectadas:
                res_s     = ses["res"]
                fecha_obj = ses.get("fecha")
                fecha_str = fecha_obj.strftime("%d %b %Y") if fecha_obj else "?"
                tipo_lbl  = ses["meta"].get("tipo", "?")
                n_ej      = len(res_s.get("datos", []))

                if not res_s.get("exito"):
                    st.error(f"No se pudo procesar {fecha_str}")
                    continue

                # Header del resultado
                garmin_html = ""
                if ses.get("vinculo_running"):
                    v  = ses["vinculo_running"]
                    km = round(float(v.get("distancia_m") or 0) / 1000, 2)
                    ri = v.get("ritmo_medio")
                    ri_txt = f" · {ri} min/km" if ri else ""
                    garmin_html = (
                        f"<div style='color:{TXT2};font-size:11px;margin-top:4px;'>"
                        f"⌚ Enlazado con actividad: {km} km{ri_txt}</div>")

                st.markdown(
                    f"<div style='background:#111f11;border:1px solid {ACCENT}30;"
                    f"border-radius:10px;padding:12px 14px;margin:8px 0;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;'>"
                    f"<span style='color:{ACCENT};font-weight:600;font-size:13px;'>"
                    f"✅ {fecha_str}</span>"
                    f"<span style='color:{TXT3};font-size:11px;'>"
                    f"{tipo_lbl} · {n_ej} ejercicio{'s' if n_ej!=1 else ''}</span>"
                    f"</div>{garmin_html}</div>",
                    unsafe_allow_html=True)

                if ses.get("nota_estado"):
                    st.warning(f"Percepción: {ses['nota_estado']}")

                if res_s["datos"]:
                    cols_show = ["ejercicio", "series", "repeticiones", "peso", "notas"]
                    df_r = pd.DataFrame(res_s["datos"])
                    df_r = df_r[[c for c in cols_show if c in df_r.columns]]
                    df_r.columns = [c.capitalize() for c in df_r.columns]
                    # Rellenar notas vacías con —
                    if "Notas" in df_r.columns:
                        df_r["Notas"] = df_r["Notas"].fillna("").replace("", "—")
                    st.dataframe(df_r, use_container_width=True, hide_index=True)
                elif ses["meta"]["has_fuerza"]:
                    st.info("No se detectaron ejercicios. Revisa el formato.")

            n = len(st.session_state.sesiones_detectadas)
            col_g, col_c = st.columns([3, 1])
            with col_g:
                if st.button(
                    f"💾 Guardar {n} sesión{'es' if n>1 else ''}",
                    use_container_width=True, type="primary"
                ):
                    _guardar_sesiones(usuario_id, st.session_state.sesiones_detectadas)
            with col_c:
                if st.button("✕ Descartar", use_container_width=True):
                    st.session_state.resultado_ia = None
                    st.session_state.sesiones_detectadas = []
                    st.rerun()

        # ── Sección 3: Lesiones activas inline ──────────────────────────
        _render_lesiones_inline(usuario_id)

    # ======================================================================
    # COLUMNA DERECHA
    # ======================================================================
    with col_der:

        # ── Sección 1: Últimas sesiones ─────────────────────────────────
        st.markdown(label_upper("Últimas sesiones"), unsafe_allow_html=True)
        conn = get_db_connection()
        try:
            df_hist = pd.read_sql_query(
                "SELECT fecha, tipo_registro, resumen FROM sesiones_fuerza "
                "WHERE usuario_id=? ORDER BY fecha DESC LIMIT 10",
                conn, params=(usuario_id,))
        except Exception:
            df_hist = pd.DataFrame()
        finally:
            conn.close()

        if df_hist.empty:
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
            for _, row in df_hist.iterrows():
                tc       = tipo_color(row.get("tipo_registro", ""))
                tipo_txt = str(row.get("tipo_registro", "")).capitalize()
                resumen  = str(row.get("resumen", ""))[:70]
                fecha_d  = str(row.get("fecha", ""))
                st.markdown(
                    f"<div style='display:flex;align-items:flex-start;gap:10px;"
                    f"padding:7px 0;border-bottom:1px solid {BORDER};'>"
                    f"<span style='width:7px;height:7px;border-radius:50%;background:{tc};"
                    f"margin-top:4px;flex-shrink:0;display:inline-block;'></span>"
                    f"<div style='min-width:0;'>"
                    f"<div style='font-size:12px;color:{TXT1};font-weight:500;"
                    f"white-space:nowrap;overflow:hidden;text-overflow:ellipsis;'>{resumen}</div>"
                    f"<div style='font-size:10px;color:{TXT3};margin-top:1px;'>"
                    f"{fecha_d} · {tipo_txt}</div>"
                    f"</div></div>",
                    unsafe_allow_html=True)

        # ── Sección 2: Calendario mensual ───────────────────────────────
        st.markdown(
            f"<div style='margin-top:20px;'></div>",
            unsafe_allow_html=True)
        st.markdown(label_upper("Calendario del mes"), unsafe_allow_html=True)

        anio_cal, mes_cal = st.session_state.cal_cursor
        MESES_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

        nav_l, nav_c, nav_r = st.columns([1, 4, 1])
        with nav_l:
            if st.button("◀", key="cal_prev"):
                m, y = mes_cal - 1, anio_cal
                if m < 1: m, y = 12, y - 1
                st.session_state.cal_cursor = (y, m)
                st.rerun()
        with nav_c:
            st.markdown(
                f"<div style='text-align:center;font-size:13px;font-weight:700;"
                f"color:{TXT1};padding:4px 0;'>"
                f"{MESES_ES[mes_cal-1]} {anio_cal}</div>",
                unsafe_allow_html=True)
        with nav_r:
            if st.button("▶", key="cal_next"):
                m, y = mes_cal + 1, anio_cal
                if m > 12: m, y = 1, y + 1
                st.session_state.cal_cursor = (y, m)
                st.rerun()

        dias_mes = _cargar_dias_mes(usuario_id, anio_cal, mes_cal)
        st.markdown(
            html_calendario_entreno(dias_mes, anio_cal, mes_cal),
            unsafe_allow_html=True)

        # Stats del mes
        n_gym = sum(1 for t in dias_mes.values() if t in ("gym", "both"))
        n_run = sum(1 for t in dias_mes.values() if t in ("run", "both"))
        n_tot = len(dias_mes)
        c1, c2, c3 = st.columns(3)
        c1.metric("Días", n_tot)
        c2.metric("🏋️ Fuerza", n_gym)
        c3.metric("🏃 Carreras", n_run)


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
        st.session_state.resultado_ia = None
        st.session_state.sesiones_detectadas = []
        st.rerun()
    except Exception as e:
        st.error(f"Error SQL: {e}")
    finally:
        conn.close()

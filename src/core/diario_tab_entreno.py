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
        "run":  {"bg": "#1a3a1a", "border": "#a3e635", "dot": "#a3e635", "emoji": "🏃"},
        "gym":  {"bg": "#1e1b3a", "border": "#818cf8", "dot": "#a78bfa", "emoji": "🏋️"},
        "both": {"bg": "#1a2a1a", "border": "#a3e635", "dot": "#a3e635", "emoji": "💪🏃"},
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
        bg     = cfg.get("bg", "#161b22")
        border = cfg.get("border", "#21262d")
        emoji  = cfg.get("emoji", "")
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

    _k_res  = f"resultado_ia_{usuario_id}"
    _k_ses  = f"sesiones_detectadas_{usuario_id}"
    _k_cal  = f"cal_cursor_{usuario_id}"
    if _k_res not in st.session_state: st.session_state[_k_res] = None
    if _k_ses not in st.session_state: st.session_state[_k_ses] = []
    if _k_cal not in st.session_state:
        hoy = date.today()
        st.session_state[_k_cal] = (hoy.year, hoy.month)

    col_izq, col_der = st.columns([1, 1], gap="large")

    # ======================================================================
    # COLUMNA IZQUIERDA
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
                "Hip Thrust 3x8 30kg  no he terminado la serie\n"
                "Búlgaras 14kg  3x8  me he sentido débil\n\n"
                "Martes\n"
                "Dominadas 3x6  no termino\n"
                "Remo abierto 3x8 27kg\n"
                "Bíceps Martillo  3x8 22kg"
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

        # ── Sección 2: Resultado ────────────────────────────────────────
        if st.session_state[_k_res] and st.session_state[_k_ses]:
            _card_open()
            for ses in st.session_state[_k_ses]:
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

                if ses.get("vinculo_running"):
                    v = ses["vinculo_running"]
                    km = round(float(v.get("distancia_m") or 0) / 1000, 2)
                    ritmo_txt = _formatear_ritmo_min_km(v.get("ritmo_medio"))
                    bpm_txt = _formatear_bpm(v.get("fc_media"))
                    partes = [f"⌚ Enlazado con Garmin · {km}km"]
                    if ritmo_txt:
                        partes.append(ritmo_txt)
                    if bpm_txt:
                        partes.append(bpm_txt)
                    st.markdown(
                        f"<div style='color:#60a5fa;font-size:11px;margin:4px 0 8px;'>"
                        f"{' · '.join(partes)}</div>",
                        unsafe_allow_html=True,
                    )

                if ses.get("nota_estado"):
                    st.warning(f"Percepción: {ses['nota_estado']}")

                if res_s["datos"]:
                    cols_show = ["ejercicio", "series", "repeticiones", "peso", "notas"]
                    df_r = pd.DataFrame(res_s["datos"])
                    df_r = df_r[[c for c in cols_show if c in df_r.columns]]
                    if not df_r.empty:
                        df_r.columns = [c.capitalize() for c in df_r.columns]
                        if "Notas" in df_r.columns:
                            df_r["Notas"] = df_r["Notas"].fillna("").replace("", "—")

                        for _, ej in df_r.iterrows():
                            nota_txt = str(ej.get("Notas", "") or "")
                            chip = _color_nota(nota_txt)
                            chip_html = ""
                            if chip:
                                _, bg_chip, fg_chip = chip
                                chip_html = (
                                    f"<span style='background:{bg_chip};color:{fg_chip};"
                                    f"border-radius:999px;padding:2px 8px;font-size:10px;"
                                    f"font-weight:600;'>"
                                    f"{nota_txt if nota_txt and nota_txt != '—' else 'Sin nota'}"
                                    f"</span>"
                                )
                            st.markdown(
                                f"<div style='display:grid;grid-template-columns:1.7fr 0.5fr 0.6fr 0.8fr 1.2fr;gap:8px;"
                                f"padding:8px 10px;border-bottom:1px solid {BORDER};align-items:center;'>"
                                f"<div style='color:{TXT1};font-size:12px;font-weight:600;'>{ej.get('Ejercicio','—')}</div>"
                                f"<div style='color:{TXT2};font-size:12px;'>{ej.get('Series','—')}</div>"
                                f"<div style='color:{TXT2};font-size:12px;'>{ej.get('Repeticiones','—')}</div>"
                                f"<div style='color:{TXT2};font-size:12px;'>{ej.get('Peso','—')}</div>"
                                f"<div>{chip_html}</div>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )
                elif ses["meta"]["has_fuerza"]:
                    st.info("No se detectaron ejercicios. Revisa el formato.")

            _card_close()

            n = len(st.session_state[_k_ses])
            col_g, col_c = st.columns([3, 1])
            with col_g:
                if st.button(
                    f"💾 Guardar {n} sesión{'es' if n>1 else ''}",
                    use_container_width=True, type="primary"
                ):
                    _guardar_sesiones(usuario_id, st.session_state[_k_ses])
            with col_c:
                if st.button("✕ Descartar", use_container_width=True):
                    st.session_state[_k_res] = None
                    st.session_state[_k_ses] = []
                    st.rerun()

        # ── Sección 3: Lesiones activas inline ──────────────────────────
        _card_open()
        _render_lesiones_inline(usuario_id)
        _card_close()

    # ======================================================================
    # COLUMNA DERECHA
    # ======================================================================
    with col_der:
        # ── Sección 1: Calendario mensual ───────────────────────────────
        _card_open()
        st.markdown(label_upper("Calendario del mes"), unsafe_allow_html=True)

        anio_cal, mes_cal = st.session_state[_k_cal]
        MESES_ES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio",
                    "Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]

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

        dias_mes = _cargar_dias_mes(usuario_id, anio_cal, mes_cal)
        st.markdown(
            html_calendario_entreno(dias_mes, anio_cal, mes_cal),
            unsafe_allow_html=True)

        _card_close()

        # ── Sección 2: Stats del mes ────────────────────────────────────
        _card_open()
        n_gym = sum(1 for t in dias_mes.values() if t in ("gym", "both"))
        n_run = sum(1 for t in dias_mes.values() if t in ("run", "both"))
        n_tot = len(dias_mes)
        st.markdown(label_upper("Stats del mes"), unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.metric("Días", n_tot)
        c2.metric("🏋️ Fuerza", n_gym)
        c3.metric("🏃 Carreras", n_run)

        _card_close()

        # ── Sección 3: Leyenda ─────────────────────────────────────────
        _card_open()
        st.markdown(label_upper("Leyenda"), unsafe_allow_html=True)
        st.markdown(
            f"<div style='display:flex;gap:12px;flex-wrap:wrap;color:{TXT2};font-size:10px;align-items:center;'>"
            f"<span style='display:flex;align-items:center;gap:6px;'><span style='width:8px;height:8px;border-radius:50%;background:#a3e635;display:inline-block;'></span>🏃 Carrera</span>"
            f"<span style='display:flex;align-items:center;gap:6px;'><span style='width:8px;height:8px;border-radius:50%;background:#a78bfa;display:inline-block;'></span>🏋️ Fuerza</span>"
            f"<span style='display:flex;align-items:center;gap:6px;'><span style='width:8px;height:8px;border-radius:50%;background:#60a5fa;display:inline-block;'></span>💪🏃 Ambos</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        _card_close()

        # ── Sección 4: Sesiones guardadas ──────────────────────────────
        _card_open()
        st.markdown(label_upper("Sesiones guardadas"), unsafe_allow_html=True)
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

        actividad_ids_vinculadas = set()
        if not df_hist.empty and "actividad_garmin_id" in df_hist.columns:
            actividad_ids_vinculadas = set(
                int(v) for v in df_hist["actividad_garmin_id"].dropna().tolist() if str(v).strip() not in ("", "None")
            )

        df_garmin_libre = df_garmin.copy()
        if not df_garmin_libre.empty and "id_actividad" in df_garmin_libre.columns and actividad_ids_vinculadas:
            df_garmin_libre = df_garmin_libre[~df_garmin_libre["id_actividad"].isin(actividad_ids_vinculadas)]

        if df_hist.empty and df_garmin_libre.empty:
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
                                c_del = get_db_connection()
                                try:
                                    c_del.execute("DELETE FROM ejercicios_fuerza WHERE sesion_id=?", (sesion_id_val,))
                                    c_del.execute("DELETE FROM sesiones_fuerza WHERE id=? AND usuario_id=?",
                                                  (sesion_id_val, usuario_id))
                                    c_del.commit()
                                finally:
                                    c_del.close()
                                st.session_state[key_confirm] = False
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

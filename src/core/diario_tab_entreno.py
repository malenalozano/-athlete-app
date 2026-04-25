"""
src/core/diario_tab_entreno.py — Tab "Entreno libre" del Diario.
Layout: izq calendario + stats sticky · der textarea + sesiones del día.
La lógica de procesado / guardado / detección queda intacta.
"""
import streamlit as st
from datetime import datetime, date

from src.db.db_manager import get_db_connection
from src.core.styles import TXT1, TXT2, TXT3, label_upper
from src.core.ejercicios_helpers import buscar_ejercicio_id, guardar_historial
from src.core.ui_helpers_a import (
    _dividir_nota_por_fechas, _clasificar_segmento_diario, _extraer_nota_estado,
    _inferir_tipo_carrera, _buscar_actividad_running_fecha,
)
from src.core.ui_helpers_b import extraer_fecha_historica
from src.core.ai_coach import procesar_nota_fuerza
from src.core.diario_ui_helpers import (
    cargar_dias_mes, html_calendario_con_seleccion, render_sesiones_del_dia,
    render_resultado_procesado, ultimo_dia_con_actividad, MESES_ES,
)

# CSS local para esta tab
_CSS_LOCAL = """<style>
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
div[data-testid="stExpander"] {
    background: #0d1117 !important;
    border: 1px solid #21262d !important;
    border-radius: 10px !important;
}
div[data-testid="stExpander"]:hover {
    border-color: #30363d !important;
}
div[data-testid="stExpander"][aria-expanded="true"] {
    border-color: rgba(163,230,53,0.25) !important;
}
div[data-testid="stExpanderDetails"] {
    border-top: 1px solid #21262d !important;
    padding-top: 12px !important;
}
</style>"""


def _stats_card(label, value, color):
    return (
        f"<div style='background:rgba(255,255,255,0.02);border:1px solid #21262d;"
        f"border-radius:10px;padding:10px 6px;text-align:center;'>"
        f"<div style='color:{color};font-size:1.4rem;font-weight:800;line-height:1;'>{value}</div>"
        f"<div style='color:#8B949E;font-size:0.62rem;font-weight:600;"
        f"text-transform:uppercase;margin-top:4px;'>{label}</div>"
        f"</div>"
    )


def _descartar_resultado(usuario_id):
    st.session_state[f"sesiones_detectadas_{usuario_id}"] = []
    st.session_state[f"resultado_ia_{usuario_id}"] = None


def render_tab_entreno(usuario_id: int):
    st.markdown(_CSS_LOCAL, unsafe_allow_html=True)

    # ── Estado ──────────────────────────────────────────────────────────
    _k_res = f"resultado_ia_{usuario_id}"
    _k_ses = f"sesiones_detectadas_{usuario_id}"
    _k_cal = f"cal_cursor_{usuario_id}"
    _k_nota = f"nota_fuerza_{usuario_id}"
    _k_limpiar = f"limpiar_nota_fuerza_{usuario_id}"
    _k_dia = f"dia_seleccionado_{usuario_id}"
    if _k_res not in st.session_state:
        st.session_state[_k_res] = None
    if _k_ses not in st.session_state:
        st.session_state[_k_ses] = []
    if st.session_state.get(_k_limpiar):
        st.session_state[_k_nota] = ""
        st.session_state[_k_limpiar] = False
    if _k_cal not in st.session_state:
        hoy = date.today()
        st.session_state[_k_cal] = (hoy.year, hoy.month)

    anio_cal, mes_cal = st.session_state[_k_cal]
    dias_mes = cargar_dias_mes(usuario_id, anio_cal, mes_cal)

    # Resolver día seleccionado: si vacío o no en este mes → último con actividad
    dia_sel = st.session_state.get(_k_dia)
    if dia_sel is None or dia_sel not in dias_mes:
        dia_sel = ultimo_dia_con_actividad(dias_mes)
        st.session_state[_k_dia] = dia_sel

    col_cal, col_main = st.columns([1, 1.4], gap="large")

    # ── Columna izquierda: calendario + stats ───────────────────────────
    with col_cal:
        st.markdown(label_upper("Calendario del mes"), unsafe_allow_html=True)
        nav_l, nav_c, nav_r = st.columns([1, 4, 1])
        with nav_l:
            if st.button("◀", key=f"cal_prev_{usuario_id}", use_container_width=True):
                m, y = mes_cal - 1, anio_cal
                if m < 1:
                    m, y = 12, y - 1
                st.session_state[_k_cal] = (y, m)
                st.session_state[_k_dia] = None
                st.rerun()
        with nav_c:
            st.markdown(
                f"<div style='text-align:center;font-size:13px;font-weight:700;"
                f"color:{TXT1};padding:4px 0;'>"
                f"{MESES_ES[mes_cal-1]} {anio_cal}</div>",
                unsafe_allow_html=True)
        with nav_r:
            if st.button("▶", key=f"cal_next_{usuario_id}", use_container_width=True):
                m, y = mes_cal + 1, anio_cal
                if m > 12:
                    m, y = 1, y + 1
                st.session_state[_k_cal] = (y, m)
                st.session_state[_k_dia] = None
                st.rerun()

        # Calendario visual con día seleccionado destacado
        st.markdown(
            html_calendario_con_seleccion(dias_mes, anio_cal, mes_cal, dia_sel),
            unsafe_allow_html=True
        )

        # Picker de día (pills) sólo para días con actividad
        if dias_mes:
            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            opciones = [f"{d:02d}" for d in sorted(dias_mes.keys())]
            default_str = f"{dia_sel:02d}" if dia_sel else None
            sel_pill = st.pills(
                "dia_picker", options=opciones, default=default_str,
                selection_mode="single", label_visibility="collapsed",
                key=f"pill_dia_{usuario_id}_{anio_cal}_{mes_cal}",
            )
            if sel_pill and int(sel_pill) != dia_sel:
                st.session_state[_k_dia] = int(sel_pill)
                st.rerun()

        # Leyenda
        st.markdown(
            f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:4px 10px;"
            f"margin-top:10px;font-size:10px;color:{TXT2};'>"
            f"<div><span style='color:#a3e635;'>●</span> Carrera</div>"
            f"<div><span style='color:#a78bfa;'>●</span> Fuerza</div>"
            f"<div><span style='color:#22d3ee;'>●</span> Ambos</div>"
            f"<div><span style='color:#93c5fd;'>●</span> Otros</div>"
            f"</div>",
            unsafe_allow_html=True)

        # Stats al pie
        n_gym = sum(1 for v in dias_mes.values()
                    if isinstance(v, dict) and v.get("tipo") in ("gym", "both"))
        n_run = sum(1 for v in dias_mes.values()
                    if isinstance(v, dict) and v.get("tipo") in ("run", "both"))
        n_tot = len(dias_mes)
        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        c1.markdown(_stats_card("📅 Días", n_tot, "#C9FF00"), unsafe_allow_html=True)
        c2.markdown(_stats_card("🏋️ Fuerza", n_gym, "#a78bfa"), unsafe_allow_html=True)
        c3.markdown(_stats_card("🏃 Carreras", n_run, "#a3e635"), unsafe_allow_html=True)

    # ── Columna derecha: textarea + sesiones del día ────────────────────
    with col_main:
        # Sección 1: entrada de texto
        st.markdown(label_upper("Entreno libre"), unsafe_allow_html=True)
        nota = st.text_area(
            "nota", height=110, key=_k_nota,
            placeholder=(
                "Lunes\n"
                "Hip Thrust 3x8 30kg - no he terminado la serie\n"
                "Búlgaras 14kg 3x8 - me he sentido débil\n"
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
            if st.button("📅 Hoy", use_container_width=True):
                st.session_state["_fecha_override"] = date.today()

        if procesar and nota.strip():
            if len(nota.strip()) > 5000:
                st.error(f"⚠️ Nota muy larga ({len(nota.strip())} caracteres). Máximo 5000.")
            else:
                sesiones_prep = []
                with st.spinner("Analizando…"):
                    for marca, frag in _dividir_nota_por_fechas(nota):
                        texto_seg = frag if marca else nota
                        fecha_seg, _ = extraer_fecha_historica(texto_seg)
                        meta = _clasificar_segmento_diario(texto_seg)
                        nota_estado = _extraer_nota_estado(texto_seg)
                        vinculo = _buscar_actividad_running_fecha(usuario_id, fecha_seg)
                        res = (procesar_nota_fuerza(texto_seg, usuario_id=usuario_id)
                               if meta["has_fuerza"]
                               else {"exito": True, "datos": [], "raw": ""})
                        sesiones_prep.append({
                            "fecha": fecha_seg, "res": res, "texto": texto_seg,
                            "meta": meta, "nota_estado": nota_estado,
                            "vinculo_running": vinculo,
                        })
                st.session_state[_k_ses] = sesiones_prep
                st.session_state[_k_res] = True
                st.rerun()

        # Resultado procesado (delegado)
        if st.session_state.get(_k_res) and st.session_state.get(_k_ses):
            render_resultado_procesado(
                usuario_id, st.session_state[_k_ses],
                on_guardar=lambda: _guardar_sesiones(usuario_id, st.session_state[_k_ses]),
                on_descartar=lambda: _descartar_resultado(usuario_id),
            )

        # Sección 2: sesiones del día seleccionado
        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        if dia_sel:
            fecha_dt = date(anio_cal, mes_cal, dia_sel)
        else:
            hoy = date.today()
            fecha_dt = hoy if (hoy.month == mes_cal and hoy.year == anio_cal) \
                       else date(anio_cal, mes_cal, 1)
        render_sesiones_del_dia(usuario_id, fecha_dt)


# ---------------------------------------------------------------------------
# Guardado en BD (lógica intacta)
# ---------------------------------------------------------------------------

def _guardar_sesiones(usuario_id, sesiones):
    conn = get_db_connection()
    try:
        for ses in sesiones:
            meta = ses["meta"]
            vinc = ses["vinculo_running"]
            res_s = ses["res"]
            tipo_reg = meta["tipo"]
            if tipo_reg == "carrera":
                resumen = f"Carrera · {_inferir_tipo_carrera(ses['texto'])}"
            elif res_s["datos"]:
                grupos = list({
                    str(e.get("grupo_muscular", "")).strip()
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
                    "grupo_muscular,musculo_principal,sensaciones) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (sesion_id, ej.get("ejercicio", ""),
                     float(ej.get("peso", 0) or 0),
                     int(ej.get("series", 0) or 0),
                     int(ej.get("repeticiones", 0) or 0),
                     ej.get("grupo_muscular", "Tren Inferior"),
                     ej.get("musculo_principal", "Varios"),
                     ej.get("notas", "")))
                ej_id = buscar_ejercicio_id(usuario_id, ej.get("ejercicio", ""))

                if not ej_id:
                    nombre_ej = ej.get("ejercicio", "").strip()
                    if nombre_ej:
                        try:
                            conn.execute(
                                "INSERT INTO ejercicios_biblioteca "
                                "(usuario_id,nombre,grupo_muscular,musculo_principal,tipo,activo,creado_en) "
                                "VALUES (?,?,?,?,?,1,?)",
                                (usuario_id, nombre_ej,
                                 ej.get("grupo_muscular", "Tren Inferior"),
                                 ej.get("musculo_principal", "Varios"),
                                 "Fuerza",
                                 datetime.now().strftime("%Y-%m-%d")))
                            ej_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                        except Exception:
                            pass

                if ej_id:
                    guardar_historial(
                        usuario_id, ej_id, fecha_str,
                        float(ej.get("peso", 0) or 0),
                        int(ej.get("series", 0) or 1),
                        int(ej.get("repeticiones", 0) or 1),
                        notas=str(ej.get("notas", "") or ""))

        conn.commit()
        st.cache_data.clear()
        n = len(sesiones)
        st.success(f"✅ {n} sesión{'es' if n > 1 else ''} guardada{'s' if n > 1 else ''}")
        st.session_state[f"resultado_ia_{usuario_id}"] = None
        st.session_state[f"sesiones_detectadas_{usuario_id}"] = []
        st.session_state[f"limpiar_nota_fuerza_{usuario_id}"] = True
        st.rerun()
    except Exception as e:
        st.error(f"Error SQL: {e}")
    finally:
        conn.close()

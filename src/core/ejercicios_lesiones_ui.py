"""
src/core/ejercicios_lesiones_ui.py
Tabs 'Ejercicios' (biblioteca + progreso) y 'Lesiones' del Diario.
"""

import json
import pandas as pd
import streamlit as st
from datetime import datetime

from src.db.db_manager import get_db_connection
from src.core.styles import (
    ACCENT, CARD, CARD2, BORDER, BORDER_H, TXT1, TXT2, TXT3,
    FUERZA, label_upper, badge,
)
from src.core.ejercicios_helpers import (
    GRUPOS as _GRUPOS_BIB, GRUPO_COLOR, stats_ejercicio, cargar_biblioteca,
)

_GRUPOS = ["Glúteo","Tren inferior","Tren superior","Espalda","Pecho","Bíceps","Tríceps","Core","Full body"]
_MUSCULOS = {
    "Glúteo":        ["Glúteo mayor","Glúteo medio","Glúteo menor"],
    "Tren inferior": ["Cuádriceps","Isquiotibiales","Gemelos","Aductores"],
    "Tren superior": ["Hombro","Deltoides","Trapecio"],
    "Espalda":       ["Dorsal","Romboides","Erector espinal"],
    "Pecho":         ["Pectoral mayor","Pectoral menor"],
    "Bíceps":        ["Bíceps braquial","Braquial"],
    "Tríceps":       ["Tríceps braquial"],
    "Core":          ["Abdomen","Oblicuos","Lumbar"],
    "Full body":     ["General"],
}
_TIPOS = ["Fuerza","Cardio","Movilidad","Técnica"]
_TIPOS_LESION = [
    "Periostitis","Tendón de Aquiles","Fascitis Plantar",
    "Rodilla inflamada","Dolor de espalda","Poleas (Dedos)",
    "Hombro inflamado","Dolor de Cadera",
]
_GRADO_COLOR = {1: ("#22c55e","Leve"), 2: ("#f59e0b","Moderada"), 3: ("#ef4444","Grave")}


def _grado_info(g):
    try:
        gi = max(1, min(3, int(g or 1)))
    except Exception:
        gi = 1
    return _GRADO_COLOR.get(gi, (TXT2, "?"))


def _card_ejercicio_html(ej: dict, stats: dict) -> str:
    ultimo  = f"{stats['ultimo_peso']} kg" if stats.get("ultimo_peso") is not None else "—"
    mejor   = f"{stats['mejor_peso']} kg"  if stats.get("mejor_peso")  is not None else "—"
    series  = str(stats["series_habitual"]) if stats.get("series_habitual") is not None else "—"
    alias_raw = ej.get("alias", "")
    try:
        alias = ", ".join(json.loads(alias_raw)) if alias_raw else "—"
    except Exception:
        alias = alias_raw or "—"
    color_g = GRUPO_COLOR.get(ej.get("grupo_muscular",""), "#8b949e")
    return f"""<div style="background:#161b22;border:1px solid #21262d;border-radius:12px;
padding:14px;margin-bottom:8px">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:10px">
        <div style="width:8px;height:8px;border-radius:50%;background:{color_g};flex-shrink:0"></div>
        <div style="font-size:13px;font-weight:500;color:#e6edf3">{ej['nombre']}</div>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-bottom:8px">
        <div style="background:#0d1117;border-radius:7px;padding:7px;text-align:center">
            <div style="font-size:14px;font-weight:500;color:#a3e635">{ultimo}</div>
            <div style="font-size:9px;color:#484f58;margin-top:2px;text-transform:uppercase">Último</div>
        </div>
        <div style="background:#0d1117;border-radius:7px;padding:7px;text-align:center">
            <div style="font-size:14px;font-weight:500;color:#f59e0b">{mejor}</div>
            <div style="font-size:9px;color:#484f58;margin-top:2px;text-transform:uppercase">Mejor</div>
        </div>
        <div style="background:#0d1117;border-radius:7px;padding:7px;text-align:center">
            <div style="font-size:14px;font-weight:500;color:#60a5fa">{series}</div>
            <div style="font-size:9px;color:#484f58;margin-top:2px;text-transform:uppercase">Series</div>
        </div>
    </div>
    <div style="font-size:10px;color:#484f58">alias: {alias}</div>
</div>"""



# ---------------------------------------------------------------------------
# TAB EJERCICIOS
# ---------------------------------------------------------------------------

def render_tab_ejercicios(usuario_id: int):
    # ── Formulario añadir (colapsado) ────────────────────────────────
    with st.expander("+ Añadir ejercicio"):
        with st.form("form_ej_nuevo", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                nombre_n = st.text_input("Nombre *", placeholder="Hip Thrust, Remo, Dominadas…")
                grupo_s  = st.selectbox("Grupo muscular", _GRUPOS)
            with c2:
                musc_s  = st.text_input("Músculo principal", placeholder="Glúteo mayor, Dorsal…")
                tipo_s  = st.selectbox("Tipo", _TIPOS)
            with c3:
                alias_n = st.text_input("Alias (separados por coma)",
                                        placeholder="HT, hip thrust…",
                                        help="Nombres coloquiales para el parser")
                notas_n = st.text_input("Notas (opcional)")
            if st.form_submit_button("Guardar ejercicio", type="primary", use_container_width=True):
                if not nombre_n.strip():
                    st.error("El nombre es obligatorio.")
                else:
                    alias_json = (json.dumps([a.strip() for a in alias_n.split(",") if a.strip()])
                                  if alias_n.strip() else None)
                    conn = get_db_connection()
                    try:
                        conn.execute(
                            "INSERT OR IGNORE INTO ejercicios_biblioteca "
                            "(usuario_id,nombre,grupo_muscular,musculo_principal,tipo,alias,notas,activo,creado_en) "
                            "VALUES (?,?,?,?,?,?,?,1,?)",
                            (usuario_id, nombre_n.strip(), grupo_s, musc_s.strip() or None,
                             tipo_s, alias_json, notas_n.strip() or None,
                             datetime.now().strftime("%Y-%m-%d")))
                        conn.commit()
                        st.success(f"'{nombre_n.strip()}' añadido.")
                    except Exception as e:
                        st.error(f"Error: {e}")
                    finally:
                        conn.close()
                    st.rerun()

    # ── Biblioteca agrupada por grupo muscular ───────────────────────
    df = cargar_biblioteca(usuario_id)
    df_activos = df[df["activo"] == 1] if not df.empty else df

    if df_activos.empty:
        st.markdown(
            f"<div style='color:{TXT3};font-size:13px;text-align:center;padding:32px 0;'>"
            f"Biblioteca vacía. Añade ejercicios con el botón de arriba.</div>",
            unsafe_allow_html=True)
        return

    grupos_presentes = df_activos["grupo_muscular"].dropna().unique().tolist()
    # Ordenar por orden definido
    orden = {g: i for i, g in enumerate(_GRUPOS)}
    grupos_presentes = sorted(grupos_presentes, key=lambda g: orden.get(g, 99))

    for grupo in grupos_presentes:
        df_g = df_activos[df_activos["grupo_muscular"] == grupo]
        color_g = GRUPO_COLOR.get(grupo, "#8b949e")
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:8px;margin:20px 0 10px;'>"
            f"<span style='width:8px;height:8px;border-radius:50%;background:{color_g};"
            f"display:inline-block;flex-shrink:0;'></span>"
            f"<span style='color:{color_g};font-size:11px;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.8px;'>{grupo}</span>"
            f"<span style='color:{TXT3};font-size:11px;'>({len(df_g)})</span></div>",
            unsafe_allow_html=True)

        cols3 = st.columns(3)
        for i, (_, row) in enumerate(df_g.iterrows()):
            ej_dict = row.to_dict()
            s = stats_ejercicio(int(row["id"]), usuario_id)
            with cols3[i % 3]:
                st.markdown(_card_ejercicio_html(ej_dict, s), unsafe_allow_html=True)
                if st.button("Archivar", key=f"arch_{row['id']}", help="Mover a archivados"):
                    conn = get_db_connection()
                    conn.execute("UPDATE ejercicios_biblioteca SET activo=0 WHERE id=?", (row["id"],))
                    conn.commit(); conn.close(); st.rerun()

    # ── Archivados ───────────────────────────────────────────────────
    df_arch = df[df["activo"] == 0] if not df.empty else pd.DataFrame()
    if not df_arch.empty:
        with st.expander(f"Archivados ({len(df_arch)})"):
            cols3 = st.columns(3)
            for i, (_, row) in enumerate(df_arch.iterrows()):
                with cols3[i % 3]:
                    st.markdown(
                        f"<div style='background:#0d1117;border:1px solid #21262d;border-radius:10px;"
                        f"padding:10px 12px;opacity:0.6;margin-bottom:6px;'>"
                        f"<div style='font-size:13px;color:#8b949e;'>{row['nombre']}</div>"
                        f"<div style='font-size:10px;color:#484f58;'>{row.get('grupo_muscular','')}</div>"
                        f"</div>", unsafe_allow_html=True)
                    if st.button("Restaurar", key=f"rest_{row['id']}"):
                        conn = get_db_connection()
                        conn.execute("UPDATE ejercicios_biblioteca SET activo=1 WHERE id=?", (row["id"],))
                        conn.commit(); conn.close(); st.rerun()


# ---------------------------------------------------------------------------
# TAB LESIONES
# ---------------------------------------------------------------------------

def render_tab_lesiones(usuario_id: int):
    conn = get_db_connection()
    try:
        df_act  = pd.read_sql_query(
            "SELECT id,tipo,grado,fecha_inicio,notas FROM lesiones "
            "WHERE usuario_id=? AND activa=1 ORDER BY grado DESC,fecha_inicio",
            conn, params=(usuario_id,))
        df_arch = pd.read_sql_query(
            "SELECT tipo,grado,fecha_inicio,fecha_fin FROM lesiones "
            "WHERE usuario_id=? AND activa=0 ORDER BY fecha_fin DESC LIMIT 10",
            conn, params=(usuario_id,))
    except Exception:
        df_act = df_arch = pd.DataFrame()
    finally:
        conn.close()

    # ── Lesiones activas ─────────────────────────────────────────────
    if df_act.empty:
        st.markdown(
            f"<div style='background:#0a1a0a;border:1px solid #22c55e30;border-radius:10px;"
            f"padding:14px 18px;color:#22c55e;font-size:13px;margin-bottom:12px;'>"
            f"✓ Sin lesiones activas. ¡Sigue así!</div>",
            unsafe_allow_html=True)
    else:
        st.markdown(label_upper(f"Lesiones activas ({len(df_act)})"), unsafe_allow_html=True)
        for _, row in df_act.iterrows():
            col_c, col_btn = _grado_info(row["grado"])
            try:
                dias = (datetime.now().date() - pd.to_datetime(row["fecha_inicio"]).date()).days
            except Exception:
                dias = "?"
            ci, cd = st.columns([5, 1])
            with ci:
                st.markdown(
                    f"<div style='background:{col_c}0d;border-left:3px solid {col_c};"
                    f"border-radius:8px;padding:10px 14px;margin-bottom:6px;'>"
                    f"<div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;'>"
                    f"<span style='font-weight:600;color:{TXT1};'>{row['tipo']}</span>"
                    f"<span style='background:{col_c}22;color:{col_c};border-radius:999px;"
                    f"padding:1px 8px;font-size:11px;font-weight:600;'>Grado {row['grado']} — {col_btn}</span>"
                    f"<span style='color:{TXT3};font-size:11px;'>Día {dias}</span></div>"
                    f"{'<div style=\"color:'+TXT2+';font-size:11px;margin-top:3px;\">'+str(row['notas'])+'</div>' if row['notas'] else ''}"
                    f"</div>",
                    unsafe_allow_html=True)
            with cd:
                if st.button("✓ Ok", key=f"cls_{row['id']}", help="Marcar como recuperada"):
                    c2 = get_db_connection()
                    c2.execute("UPDATE lesiones SET activa=0,fecha_fin=? WHERE id=?",
                               (datetime.now().strftime("%Y-%m-%d"), row["id"]))
                    c2.commit(); c2.close(); st.rerun()

    st.divider()

    # ── Registrar nueva ──────────────────────────────────────────────
    st.markdown(label_upper("Registrar lesión"), unsafe_allow_html=True)
    with st.form("form_lesion", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            tipo_s  = st.selectbox("Zona / Tipo", _TIPOS_LESION)
            grado_s = st.select_slider(
                "Grado",
                options=[1, 2, 3],
                value=1,
                format_func=lambda x: {1: "1 — Leve", 2: "2 — Moderada", 3: "3 — Grave"}[x])
        with c2:
            f_ini   = st.date_input("Fecha inicio", value=datetime.now().date())
            notas_s = st.text_input("Notas", placeholder="Aparece al bajar escaleras…")

        if st.form_submit_button("Registrar", type="primary", use_container_width=True):
            c3 = get_db_connection()
            c3.execute(
                "INSERT INTO lesiones (usuario_id,tipo,grado,fecha_inicio,activa,notas) VALUES (?,?,?,?,1,?)",
                (usuario_id, tipo_s, grado_s, str(f_ini), notas_s.strip() or None))
            c3.commit(); c3.close()
            st.success(f"'{tipo_s}' registrada."); st.rerun()

    # ── Historial archivadas ─────────────────────────────────────────
    if not df_arch.empty:
        with st.expander(f"Historial resueltas ({len(df_arch)})"):
            st.dataframe(df_arch, use_container_width=True, hide_index=True)

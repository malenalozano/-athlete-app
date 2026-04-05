"""
pages/5_ejercicios.py — Biblioteca de ejercicios + historial de pesos.
Max 200 líneas; lógica pesada en src/core/ejercicios_helpers.py.
"""

import streamlit as st

from src.core.navbar import render_navbar
from src.core.styles import ACCENT, BORDER, TXT2, TXT3
from src.core.ejercicios_helpers import (
    GRUPOS, GRUPO_COLOR,
    cargar_biblioteca, stats_ejercicio,
    render_card_ejercicio, render_formulario_nuevo,
)
from src.db.db_manager import get_db_connection

render_navbar("ejercicios")

if "usuario_id" not in st.session_state:
    st.warning("Selecciona tu perfil en la página de inicio.")
    st.stop()
user_actual = st.session_state.usuario_id

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
col_h, col_btn = st.columns([5, 1])
with col_h:
    st.markdown(
        f"<h2 style='color:#e6edf3;font-weight:600;margin:8px 0 4px;'>Biblioteca de ejercicios</h2>"
        f"<p style='color:{TXT2};font-size:13px;margin:0 0 12px;'>"
        f"Tus ejercicios habituales · Los alias permiten que el diario libre los reconozca</p>",
        unsafe_allow_html=True)
with col_btn:
    mostrar_form = st.toggle("＋ Añadir", value=False, key="toggle_form")

# ---------------------------------------------------------------------------
# Formulario de añadir (colapsable)
# ---------------------------------------------------------------------------
if mostrar_form:
    with st.expander("Nuevo ejercicio", expanded=True):
        render_formulario_nuevo(user_actual)

# ---------------------------------------------------------------------------
# Barra de búsqueda + filtro por grupo
# ---------------------------------------------------------------------------
col_s, col_f = st.columns([3, 5])
with col_s:
    busqueda = st.text_input("🔍", placeholder="Buscar ejercicio…", label_visibility="collapsed")
with col_f:
    grupo_filtro = st.pills(
        "grupo", ["Todos"] + GRUPOS,
        selection_mode="single", default="Todos",
        label_visibility="collapsed")

# ---------------------------------------------------------------------------
# Cargar biblioteca
# ---------------------------------------------------------------------------
df = cargar_biblioteca(user_actual)
df_activos = df[df["activo"] == 1].copy() if not df.empty else df

# Aplicar filtros
if busqueda.strip() and not df_activos.empty:
    mask = df_activos["nombre"].str.contains(busqueda, case=False, na=False)
    df_activos = df_activos[mask]

if grupo_filtro and grupo_filtro != "Todos" and not df_activos.empty:
    df_activos = df_activos[df_activos["grupo_muscular"] == grupo_filtro]

# ---------------------------------------------------------------------------
# Ejercicios activos — agrupados por grupo muscular
# ---------------------------------------------------------------------------
if df_activos.empty:
    st.markdown(
        f"<div style='text-align:center;padding:40px 0;color:{TXT3};'>Sin ejercicios. Añade el primero.</div>",
        unsafe_allow_html=True)
else:
    grupos_presentes = df_activos["grupo_muscular"].dropna().unique().tolist()
    orden_grupos = [g for g in GRUPOS if g in grupos_presentes] + \
                   [g for g in grupos_presentes if g not in GRUPOS]

    for grupo in orden_grupos:
        df_g = df_activos[df_activos["grupo_muscular"] == grupo]
        gc = GRUPO_COLOR.get(grupo, TXT2)
        st.markdown(
            f"<div style='border-left:3px solid {gc};padding-left:10px;margin:20px 0 10px;'>"
            f"<span style='color:{gc};font-size:10px;font-weight:700;text-transform:uppercase;"
            f"letter-spacing:0.8px;'>{grupo}</span>"
            f"<span style='color:{TXT3};font-size:11px;margin-left:8px;'>({len(df_g)} ejercicios)</span>"
            f"</div>",
            unsafe_allow_html=True)

        cols = st.columns(2)
        for i, (_, row) in enumerate(df_g.iterrows()):
            with cols[i % 2]:
                s = stats_ejercicio(int(row["id"]), user_actual)
                render_card_ejercicio(row, s, user_actual)

# ---------------------------------------------------------------------------
# Archivados
# ---------------------------------------------------------------------------
df_arch = df[df["activo"] == 0] if not df.empty else df
if not df_arch.empty:
    with st.expander(f"Archivados ({len(df_arch)})"):
        for _, row in df_arch.iterrows():
            ca, cb = st.columns([5, 1])
            with ca:
                st.markdown(
                    f"<span style='color:{TXT2};font-size:13px;'>{row['nombre']}</span>"
                    f"<span style='color:{TXT3};font-size:11px;margin-left:8px;'>{row.get('grupo_muscular','')}</span>",
                    unsafe_allow_html=True)
            with cb:
                if st.button("Restaurar", key=f"rest_{row['id']}"):
                    c = get_db_connection()
                    c.execute("UPDATE ejercicios_biblioteca SET activo=1 WHERE id=?", (row["id"],))
                    c.commit(); c.close(); st.rerun()

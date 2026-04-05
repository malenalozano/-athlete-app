"""
src/core/ejercicios_helpers.py
Helpers de DB + UI para pages/5_ejercicios.py.
"""

import json
import pandas as pd
import streamlit as st
from datetime import datetime

from src.db.db_manager import get_db_connection
from src.core.styles import ACCENT, CARD, BORDER, BORDER_H, TXT1, TXT2, TXT3, FUERZA, label_upper

GRUPOS = [
    "Glúteo", "Tren inferior", "Tren superior",
    "Espalda", "Pecho", "Bíceps", "Tríceps", "Core", "Full body",
]
TIPOS = ["Fuerza", "Cardio", "Movilidad", "Técnica"]

GRUPO_COLOR = {
    "Glúteo":        "#a78bfa",
    "Tren inferior": "#818cf8",
    "Tren superior": "#38bdf8",
    "Espalda":       "#22d3ee",
    "Pecho":         "#fb923c",
    "Bíceps":        "#34d399",
    "Tríceps":       "#4ade80",
    "Core":          ACCENT,
    "Full body":     "#f472b6",
}


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def cargar_biblioteca(usuario_id: int) -> pd.DataFrame:
    conn = get_db_connection()
    try:
        return pd.read_sql_query(
            "SELECT id, nombre, grupo_muscular, musculo_principal, tipo, alias, notas, activo "
            "FROM ejercicios_biblioteca WHERE usuario_id=? ORDER BY grupo_muscular, nombre",
            conn, params=(usuario_id,))
    except Exception:
        return pd.DataFrame()
    finally:
        conn.close()


def stats_ejercicio(ejercicio_id: int, usuario_id: int) -> dict:
    """Último peso, mejor peso y series habituales desde historial_ejercicio."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT peso, series, repeticiones, fecha FROM historial_ejercicio "
            "WHERE ejercicio_id=? AND usuario_id=? ORDER BY fecha DESC LIMIT 20",
            (ejercicio_id, usuario_id)).fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()
    if not rows:
        return {"ultimo_peso": None, "mejor_peso": None, "series_habitual": None, "ultimo_fecha": None}
    pesos  = [r[0] for r in rows if r[0]]
    series = [r[1] for r in rows if r[1]]
    return {
        "ultimo_peso":   rows[0][0],
        "mejor_peso":    max(pesos)  if pesos  else None,
        "series_habitual": max(set(series), key=series.count) if series else None,
        "ultimo_fecha":  rows[0][3],
    }


def buscar_ejercicio_id(usuario_id: int, nombre: str) -> int | None:
    """Busca en biblioteca por nombre exacto o alias (JSON)."""
    conn = get_db_connection()
    try:
        rows = conn.execute(
            "SELECT id, nombre, alias FROM ejercicios_biblioteca WHERE usuario_id=? AND activo=1",
            (usuario_id,)).fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()
    nombre_l = nombre.lower().strip()
    for eid, enombre, ealias in rows:
        if nombre_l == enombre.lower():
            return eid
        if ealias:
            try:
                aliases = [a.lower() for a in json.loads(ealias)]
            except Exception:
                aliases = [ealias.lower()]
            if any(nombre_l in a or a in nombre_l for a in aliases):
                return eid
    return None


def guardar_historial(usuario_id: int, ejercicio_id: int, fecha: str,
                      peso: float, series: int, reps: int, rpe: int = 6, notas: str = ""):
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO historial_ejercicio (ejercicio_id,usuario_id,fecha,peso,series,repeticiones,rpe,notas) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (ejercicio_id, usuario_id, fecha, peso, series, reps, rpe, notas))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# UI helpers
# ---------------------------------------------------------------------------

def _stat_chip(label: str, value, color: str = TXT2) -> str:
    val_txt = str(value) if value is not None else "—"
    return (f"<div style='text-align:center;'>"
            f"<div style='color:{color};font-weight:700;font-size:13px;'>{val_txt}</div>"
            f"<div style='color:{TXT3};font-size:10px;text-transform:uppercase;"
            f"letter-spacing:0.5px;'>{label}</div></div>")


def render_card_ejercicio(row: pd.Series, stats: dict, usuario_id: int):
    gc = GRUPO_COLOR.get(row.get("grupo_muscular",""), TXT2)
    alias_list = []
    if row.get("alias"):
        try:
            alias_list = json.loads(row["alias"])
        except Exception:
            alias_list = [str(row["alias"])]

    alias_html = " ".join(
        f"<span style='background:{gc}18;color:{gc};border-radius:999px;"
        f"padding:1px 7px;font-size:10px;'>{a}</span>"
        for a in alias_list[:4])

    ultimo   = f"{stats['ultimo_peso']} kg" if stats["ultimo_peso"] is not None else "—"
    mejor    = f"{stats['mejor_peso']} kg"  if stats["mejor_peso"]  is not None else "—"
    series_h = str(stats["series_habitual"]) if stats["series_habitual"] is not None else "—"

    st.markdown(
        f"<div style='background:{CARD};border:1px solid {BORDER};border-radius:12px;"
        f"padding:14px 16px;margin-bottom:8px;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;'>"
        f"<div>"
        f"<span style='font-weight:600;color:{TXT1};font-size:14px;'>{row['nombre']}</span>"
        f"<span style='margin-left:8px;background:{gc}22;color:{gc};border-radius:999px;"
        f"padding:1px 8px;font-size:10px;font-weight:600;'>{row.get('tipo','')}</span>"
        f"</div>"
        f"<span style='color:{TXT3};font-size:11px;'>{row.get('musculo_principal','')}</span>"
        f"</div>"
        f"<div style='display:flex;gap:20px;padding:8px 0;border-top:1px solid {BORDER};"
        f"border-bottom:1px solid {BORDER};margin:6px 0;'>"
        f"{_stat_chip('Último',  ultimo,  ACCENT)}"
        f"{_stat_chip('Mejor',   mejor,   '#f59e0b')}"
        f"{_stat_chip('Series',  series_h, TXT2)}"
        f"</div>"
        f"<div style='margin-top:6px;display:flex;gap:4px;flex-wrap:wrap;'>{alias_html}</div>"
        f"</div>",
        unsafe_allow_html=True)

    # Botón archivar
    if st.button("Archivar", key=f"arch_{row['id']}", help="Mover a archivados"):
        c2 = get_db_connection()
        c2.execute("UPDATE ejercicios_biblioteca SET activo=0 WHERE id=?", (row["id"],))
        c2.commit(); c2.close(); st.rerun()


def render_formulario_nuevo(usuario_id: int):
    with st.form("form_nuevo_ej", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            nombre  = st.text_input("Nombre *", placeholder="Hip Thrust, Remo, Dominadas…")
            grupo   = st.selectbox("Grupo muscular", GRUPOS)
            musculo = st.text_input("Músculo principal", placeholder="Glúteo mayor, Dorsal…")
        with c2:
            tipo    = st.selectbox("Tipo", TIPOS)
            alias   = st.text_input("Alias / variantes (separados por coma)",
                                    placeholder="HT, hip thrust, glute bridge…",
                                    help="Nombres coloquiales que reconocerá el diario libre")
            notas   = st.text_input("Notas (opcional)", placeholder="Con barra olímpica…")

        if st.form_submit_button("Guardar ejercicio", type="primary", use_container_width=True):
            if not nombre.strip():
                st.error("El nombre es obligatorio.")
                return
            alias_json = json.dumps([a.strip() for a in alias.split(",") if a.strip()]) if alias.strip() else None
            conn = get_db_connection()
            try:
                conn.execute(
                    "INSERT OR IGNORE INTO ejercicios_biblioteca "
                    "(usuario_id,nombre,grupo_muscular,musculo_principal,tipo,alias,notas,activo,creado_en) "
                    "VALUES (?,?,?,?,?,?,?,1,?)",
                    (usuario_id, nombre.strip(), grupo, musculo.strip() or None,
                     tipo, alias_json, notas.strip() or None,
                     datetime.now().strftime("%Y-%m-%d")))
                conn.commit()
                st.success(f"'{nombre.strip()}' añadido a la biblioteca.")
            except Exception as e:
                st.error(f"Error: {e}")
            finally:
                conn.close()
            st.rerun()

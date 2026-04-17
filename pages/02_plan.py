"""
pages/2_plan.py — Plan semanal rediseñado.
Sub-tabs: Generar Plan (cards de días) | Datos (análisis completo del entrenador).
"""
import pandas as pd
import streamlit as st
import re
from datetime import datetime, timedelta
from html import escape

from src.core.navbar import render_navbar
from src.db.db_manager import get_db_connection, obtener_perfil as _obtener_perfil
from src.core.plan_ui_helpers import (
    html_detalle_carrera, html_detalle_fuerza, html_detalle_descanso,
)

try:
    from streamlit_sortables import sort_items
    _SORTABLES_IMPORT_ERROR = ""
except Exception as e:
    sort_items = None
    _SORTABLES_IMPORT_ERROR = str(e)

render_navbar("plan")

if "usuario_id" not in st.session_state:
    st.warning("Selecciona tu perfil en la página de inicio.")
    st.stop()
user_actual = st.session_state.usuario_id

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
_TIPOS_CARRERA = {"Tirada Larga", "Progresiva", "Carrera Z2", "Regenerativo",
                  "Tempo (umbral)", "Intervalos VO2max", "Rodaje Corto",
                  "Fartlek", "Sustitución", "Calidad"}
_TIPOS_FUERZA  = {
    "Fuerza", "Fuerza Activ.", "Fuerza Tren Superior",
    "Fuerza Push", "Fuerza Pull", "Fuerza Pierna", "Movilidad"
}
_EMOJIS = {"Tirada Larga":"🏃","Progresiva":"📈","Tempo (umbral)":"⚡",
           "Intervalos VO2max":"🔥","Carrera Z2":"🚶","Regenerativo":"💧",
           "Fuerza":"💪","Fuerza Activ.":"💪","Fuerza Tren Superior":"💪",
           "Fuerza Push":"💪","Fuerza Pull":"💪","Fuerza Pierna":"💪",
           "Descanso":"🛌","Movilidad":"🧘","Sustitución":"🔄","Rodaje Corto":"🏃"}
_BADGE = {"Fuerza":"#a855f7","Tirada Larga":"#C9FF00","Progresiva":"#C9FF00",
          "Carrera Z2":"#22c55e","Tempo (umbral)":"#f97316","Regenerativo":"#00D4FF",
          "Intervalos VO2max":"#ef4444","Fuerza Push":"#a855f7","Fuerza Pull":"#a855f7",
          "Fuerza Pierna":"#a855f7","Descanso":"#3a4150","Movilidad":"#3a4150"}
_TYPE_COLORS = {"running":"#22d3ee", "strength":"#c084fc", "rest":"#4ade80", "default":"#C9FF00"}
_DIA_CORTO = ["LUN", "MAR", "MIE", "JUE", "VIE", "SAB", "DOM"]

# ---------------------------------------------------------------------------
# CSS global: radio como tarjeta clickable vertical
# ---------------------------------------------------------------------------
st.markdown("""<style>
/* ── Botones primarios ───────────────────────────────────────── */
div[data-testid="stButton"] > button[kind="primary"] {
    border-radius: 12px !important;
    font-weight: 700 !important;
    box-shadow: 0 0 20px rgba(0,212,255,0.25) !important;
}

/* ── Radio como tarjeta ─────────────────────────────────────── */
div[data-testid="stRadio"] > div[role="radiogroup"] { gap:0!important;display:flex;flex-wrap:wrap; }
div[data-testid="stRadio"] label {
    background:#131D2B;border:1px solid rgba(201,255,0,0.15);border-radius:10px;
    padding:10px 12px;margin-bottom:6px;margin-right:6px;cursor:pointer;flex:1;min-width:150px;
    color:#C9E1FF!important;font-size:0.84rem;display:flex;align-items:center;justify-content:center; }
div[data-testid="stRadio"] label:has(input[type="radio"]:checked) {
    border-color:#C9FF00!important;background:#111f11!important;color:#C9FF00!important; }
div[data-testid="stRadio"] input[type="radio"] { display:none; }

/* ── KPI card ────────────────────────────────────────────────── */
.plan-kpi-card {
    min-height:92px;display:flex;flex-direction:column;justify-content:space-between;border-radius:14px;
}

/* ── Tarjeta de día (Figma style) ────────────────────────────── */
.plan-day-card {
    background: rgba(22,27,34,0.9);
    border-radius: 12px;
    padding: 14px 12px;
    min-height: 155px;
    position: relative;
    transition: transform 0.15s ease, box-shadow 0.15s ease;
    cursor: pointer;
}
.plan-day-card:hover { transform: translateY(-2px); }
.plan-day-card.selected {
    box-shadow: 0 0 0 2px rgba(201,255,0,0.5), 0 0 20px rgba(201,255,0,0.12) !important;
}
.plan-day-label {
    font-size:10px; color:#8B949E; font-weight:800;
    text-transform:uppercase; letter-spacing:.1em; margin:0 0 2px;
}
.plan-day-date { font-size:11px; color:#C8D1D9; font-weight:600; margin:0 0 10px; }
.plan-day-activity { font-size:12px; font-weight:800; margin:0 0 4px; line-height:1.2; }
.plan-day-duration { font-size:10px; color:#8B949E; margin:0 0 8px; }
.plan-day-badge {
    display:inline-block; font-size:9px; font-weight:700;
    padding:2px 8px; border-radius:20px; border:1px solid;
}

/* ── Sortable drag-and-drop ──────────────────────────────────── */
.sortable-component {
    display:grid!important;
    grid-template-columns:repeat(7,minmax(0,1fr))!important;
    gap:.4rem!important;
    align-items:start!important;
}
.sortable-container {
    background:rgba(15,22,35,0.85)!important;
    border:1px solid rgba(255,255,255,0.07)!important;
    border-radius:10px!important;
    padding:6px!important;
}
.sortable-container-header {
    color:#8B949E!important;
    font-size:.65rem!important;
    font-weight:800!important;
    text-transform:uppercase!important;
    letter-spacing:.1em!important;
    padding:4px 6px!important;
    border-bottom:1px solid rgba(255,255,255,0.05)!important;
    margin-bottom:4px!important;
}
.sortable-container-body { min-height:48px!important; padding:2px!important; }
.sortable-item {
    background:rgba(30,42,60,0.9)!important;
    border:1px solid rgba(255,255,255,0.08)!important;
    color:#C8D1D9!important;
    border-radius:7px!important;
    font-size:.68rem!important;
    font-weight:600!important;
    padding:5px 7px!important;
    cursor:grab!important;
    line-height:1.3!important;
}
.sortable-item:hover {
    background:rgba(40,58,85,0.9)!important;
    border-color:rgba(201,255,0,0.3)!important;
    color:white!important;
}

/* ── Botón "Ver detalle" en tarjeta ─────────────────────────── */
.plan-day-btn button {
    border-radius:8px!important;
    font-size:11px!important;
    font-weight:700!important;
    padding:4px 0!important;
    height:28px!important;
    min-height:28px!important;
}

/* ── Panel de detalle del día ────────────────────────────────── */
.plan-detail-panel {
    background: rgba(14,17,23,0.97);
    border: 1px solid rgba(201,255,0,0.2);
    border-radius: 16px;
    overflow: hidden;
    margin-top: 1.5rem;
}

</style>""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _lunes_de(dt): return dt - timedelta(days=dt.weekday())

def _km_hechos_semana(usuario_id: int, lunes: datetime) -> float:
    """Suma km de carrera realizados entre lunes y domingo (incluidos)."""
    domingo = lunes + timedelta(days=6)
    _tipos_carrera = (
        "('running', 'trail_running', 'treadmill', "
        "'indoor_running', 'track_running', 'road_running')"
    )
    conn = None
    try:
        conn = get_db_connection()
        row = conn.execute(
            f"""
            SELECT COALESCE(SUM(COALESCE(distancia_m, 0)), 0)
            FROM actividades_garmin
            WHERE usuario_id=?
              AND fecha>=?
              AND fecha<=?
              AND (tipo_deporte IN {_tipos_carrera} OR tipo_deporte IS NULL)
            """,
            (usuario_id, lunes.strftime("%Y-%m-%d"), domingo.strftime("%Y-%m-%d")),
        ).fetchone()
        return round(float((row[0] if row else 0) or 0) / 1000, 1)
    except Exception:
        return 0.0
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

def _descomponer_recomendacion(texto: str) -> tuple[str, str, str]:
    """Convierte una alerta libre en icono, titulo y descripcion legibles."""
    bruto = str(texto or "").strip()
    if not bruto:
        return "💡", "Recomendacion semanal", ""

    icono = "💡"
    trozos = bruto.split(" ", 1)
    if trozos and trozos[0] and not trozos[0][0].isalnum():
        icono = trozos[0]
        bruto = trozos[1].strip() if len(trozos) > 1 else ""

    titulo, desc = bruto, ""
    for sep in (" — ", ": "):
        if sep in bruto:
            titulo, desc = bruto.split(sep, 1)
            titulo, desc = titulo.strip(), desc.strip()
            break

    if not desc and len(titulo) > 96:
        punto = titulo.find(". ")
        if 25 <= punto <= 90:
            desc = titulo[punto + 2 :].strip()
            titulo = titulo[: punto + 1].strip()

    if not titulo:
        titulo = "Recomendacion semanal"
    return icono, titulo, desc

def _estilo_recomendacion(texto: str) -> tuple[str, str]:
    t = str(texto or "").lower()
    if any(k in t for k in ("🚫", "⛔", "bloque", "prohib")):
        return "#fca5a5", "rgba(239,68,68,0.10)"
    if any(k in t for k in ("⚠", "fatiga", "reduc", "insuficiente")):
        return "#fbbf24", "rgba(251,191,36,0.10)"
    if any(k in t for k in ("✅", "seguir", "ok", "completado")):
        return "#86efac", "rgba(34,197,94,0.10)"
    return "#67e8f9", "rgba(255,255,255,0.03)"

def _rango_semana_es(lunes: datetime) -> str:
    """Format week range in Spanish, e.g. '6-12 abril'."""
    fin = lunes + timedelta(days=6)
    meses = {
        1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio",
        7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
    }
    if lunes.month == fin.month:
        return f"{lunes.day}-{fin.day} {meses[fin.month]}"
    return f"{lunes.day} {meses[lunes.month]}-{fin.day} {meses[fin.month]}"

def _cargar_plan_de_bd(usuario_id: int, lunes: datetime) -> dict | None:
    def _extraer_km_texto(txt: str) -> float:
        m = re.search(r"(\d+(?:[\.,]\d+)?)\s*km\b", str(txt or ""), flags=re.IGNORECASE)
        if not m:
            return 0.0
        try:
            return float(m.group(1).replace(",", "."))
        except Exception:
            return 0.0

    conn = get_db_connection()
    try:
        semana_str = lunes.strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT fecha, tipo, sesion, duracion_min, intensidad FROM plan_entrenamiento "
            "WHERE usuario_id=? AND semana_inicio=? ORDER BY fecha",
            (usuario_id, semana_str)).fetchall()
        if not rows:
            return None
        dias = [{
            "fecha": r[0], "dia": datetime.fromisoformat(r[0]).strftime("%a").upper()[:3],
            "tipo": r[1], "descripcion_ia": r[2] or "", "duracion_min": r[3] or 0,
            "intensidad": r[4] or "Z1-Z2", "km": 0, "alerta": "",
        } for r in rows]
        try:
            from src.plan.motor import generar_plan_semana
            base = generar_plan_semana(usuario_id, lunes)
            if isinstance(base, dict):
                base_dias = base.get("dias", []) if isinstance(base.get("dias", []), list) else []
                km_por_fecha_tipo = {
                    (str(x.get("fecha", ""))[:10], str(x.get("tipo", ""))): float(x.get("km") or 0)
                    for x in base_dias
                }
                km_por_fecha_running = {}
                for x in base_dias:
                    _fx = str(x.get("fecha", ""))[:10]
                    _tx = str(x.get("tipo", ""))
                    _kx = float(x.get("km") or 0)
                    if _tx in _TIPOS_CARRERA and _kx > km_por_fecha_running.get(_fx, 0.0):
                        km_por_fecha_running[_fx] = _kx

                for d in dias:
                    if d.get("tipo") in _TIPOS_CARRERA and float(d.get("km") or 0) <= 0:
                        fecha = str(d.get("fecha", ""))[:10]
                        tipo = str(d.get("tipo", ""))
                        km_rec = km_por_fecha_tipo.get((fecha, tipo), 0.0)
                        if km_rec <= 0:
                            km_rec = km_por_fecha_running.get(fecha, 0.0)
                        if km_rec <= 0:
                            km_rec = _extraer_km_texto(d.get("descripcion_ia", ""))
                        if km_rec > 0:
                            d["km"] = round(km_rec, 1)

                base["km_totales"] = round(sum(float(d.get("km") or 0) for d in dias), 1)
                base["dias"] = dias; base["existe_en_bd"] = True
                return base
        except Exception:
            pass
        return {
            "dias": dias,
            "fase": {"fase_nombre": "Plan guardado", "km_semanales_max": 0, "dias_fuerza": 0},
            "semaforo": {"color": "ambar", "mensaje": "Plan recuperado desde BD",
                         "permitir_calidad": True, "multiplicador_volumen": 1.0},
            "km_totales": round(sum(float(d.get("km") or 0) for d in dias), 1),
            "acwr": None, "alertas": [], "existe_en_bd": True,
        }
    except Exception:
        return None
    finally:
        conn.close()

def _adaptar_plan_a_hoy(plan: dict, usuario_id: int, lunes: datetime, hoy: datetime) -> dict:
    hoy_date = hoy.date()
    dias_adaptados = []
    dias_pasados = (hoy_date - lunes.date()).days
    if dias_pasados > 0:
        conn = get_db_connection()
        try:
            actvs = conn.execute(
                "SELECT fecha, tipo_deporte, ROUND(CAST(tiempo_seg AS REAL)/60, 1) as duracion_min, distancia_m/1000.0 FROM actividades_garmin "
                "WHERE usuario_id=? AND fecha >= ? AND fecha < ? ORDER BY fecha",
                (usuario_id, lunes.strftime("%Y-%m-%d"), hoy_date)).fetchall()
            for i in range(dias_pasados):
                fd = lunes + timedelta(days=i)
                a = next((x for x in actvs if x[0][:10] == fd.strftime("%Y-%m-%d")), None)
                if i < len(plan.get("dias", [])):
                    dia_plan = plan["dias"][i]
                    if a:
                        # Día pasado con actividad realizada
                        dias_adaptados.append({"fecha": a[0][:10], "dia": fd.strftime("%a").upper()[:3],
                                               "tipo": "Realizado: " + (a[1] or "Actividad"),
                                               "km": a[3] or 0, "duracion_min": a[2] or 0,
                                               "intensidad": "Histórico", "descripcion_ia": "[Historial Garmin]",
                                               "alerta": "✓ Completado"})
                    else:
                        # Día pasado SIN actividad — mostrar lo que se planificó
                        dias_adaptados.append(dia_plan)
        finally:
            conn.close()
    for dia in plan.get("dias", []):
        if datetime.fromisoformat(dia["fecha"]).date() >= hoy_date:
            dias_adaptados.append(dia)
    plan["dias"] = dias_adaptados
    return plan

def _auto_guardar(usuario_id, lunes, plan_nuevo):
    semana_str = lunes.strftime("%Y-%m-%d")
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM plan_entrenamiento WHERE usuario_id=? AND semana_inicio=?",
                     (usuario_id, semana_str))
        for d in plan_nuevo.get("dias", []):
            desc = d.get("descripcion_ia") or d.get("alerta", "")
            conn.execute(
                "INSERT INTO plan_entrenamiento "
                "(usuario_id,semana_inicio,fecha,tipo,sesion,duracion_min,intensidad,creado_en) "
                "VALUES (?,?,?,?,?,?,?,?)",
                (usuario_id, semana_str, d["fecha"], d["tipo"], desc,
                 d["duracion_min"], d["intensidad"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit(); st.cache_data.clear()
    except Exception:
        pass
    finally:
        conn.close()

def _section(icon, title, color="#C9FF00"):
    grad = f"rgba({','.join(str(int(color.lstrip('#')[i:i+2],16)) for i in (0,2,4))},0.35)" if color.startswith('#') else "rgba(201,255,0,0.35)"
    st.markdown(f"""
<div style="display:flex;align-items:center;gap:0.5rem;margin:1.25rem 0 0.75rem;">
  <span style="color:{color};font-size:1rem;">{icon}</span>
  <span style="font-size:0.8rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.07em;">{title}</span>
  <div style="flex:1;height:1px;background:linear-gradient(90deg,{grad},transparent);margin-left:.5rem;"></div>
</div>""", unsafe_allow_html=True)

def _metric_card(col, label, value, sub="", color="#C9FF00"):
    sub_html = f"<div style='color:#6b7280;font-size:0.7rem;margin-top:2px;'>{sub}</div>" if sub else ""
    col.markdown(
        f"<div class='plan-kpi-card' style='background:linear-gradient(135deg,#0f1724,#101928);border:1px solid {color}33;padding:0.95rem 1rem;'>"
        f"<div style='color:#8B949E;font-size:0.65rem;font-weight:700;text-transform:uppercase;"
        f"letter-spacing:.07em;margin-bottom:4px;'>{label}</div>"
        f"<div style='color:{color};font-size:1.25rem;font-weight:800;'>{value}</div>"
        f"{sub_html}"
        f"</div>", unsafe_allow_html=True)

def _kpi_card(col, icon, label, value, color, bg, border):
    """Render a KPI card with icon, label, and value."""
    col.markdown(f"""
<div style="background:{bg};border:1px solid {border};border-radius:12px;padding:1rem;">
  <div style="display:flex;align-items:center;gap:.5rem;margin-bottom:.5rem;">
    <span style="color:{color};font-size:1rem;">{icon}</span>
    <span style="color:#8B949E;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;">{label}</span>
  </div>
  <p style="color:white;font-size:1.5rem;font-weight:800;margin:0;">{value}</p>
</div>""", unsafe_allow_html=True)

def _get_activity_type(tipo: str) -> str:
    """Classify activity type into running, strength, or rest."""
    if tipo in _TIPOS_FUERZA or "Fuerza" in tipo:
        return "strength"
    elif tipo == "Descanso" or "Descanso" in tipo:
        return "rest"
    elif tipo in _TIPOS_CARRERA:
        return "running"
    return "default"

def _get_activity_color(tipo: str) -> str:
    """Get color for activity type."""
    activity_type = _get_activity_type(tipo)
    return _TYPE_COLORS.get(activity_type, _TYPE_COLORS["default"])


def _formatear_slot_fecha(fecha_iso: str) -> str:
    try:
        return datetime.fromisoformat(fecha_iso).strftime("%d/%m")
    except Exception:
        return fecha_iso[5:] if len(fecha_iso) >= 10 else fecha_iso


def _build_sort_item(slot_idx: int, dia: dict) -> str:
    tipo = str(dia.get("tipo", "Sesion"))
    emoji = _EMOJIS.get(tipo, "📅")
    fecha_txt = _formatear_slot_fecha(str(dia.get("fecha", "")))
    dur = float(dia.get("duracion_min") or 0)
    km = float(dia.get("km") or 0)
    es_running = _get_activity_type(tipo) == "running"
    if es_running and km > 0 and dur > 0:
        carga = f"{km:.1f} km · {dur:.0f} min"
    elif km > 0:
        carga = f"{km:.1f} km"
    elif dur > 0:
        carga = f"{dur:.0f} min"
    else:
        carga = "—"
    return f"{_DIA_CORTO[slot_idx]} {fecha_txt}\n{emoji} {tipo}\n{carga}"


def _reaplicar_slots_semana(dias_ordenados: list[dict], lunes_semana: datetime) -> list[dict]:
    out: list[dict] = []
    for idx, d in enumerate(dias_ordenados):
        slot_fecha = (lunes_semana + timedelta(days=idx)).strftime("%Y-%m-%d")
        nuevo = dict(d)
        nuevo["fecha"] = slot_fecha
        nuevo["dia"] = _DIA_CORTO[idx] if idx < len(_DIA_CORTO) else nuevo.get("dia", "DIA")
        out.append(nuevo)
    return out


def _map_sorted_labels_to_days(sorted_labels: list[str], original_labels: list[str], original_days: list[dict]) -> list[dict]:
    """Resuelve el orden devuelto por el sortable de forma robusta ante cambios de espacios/saltos."""

    def _norm(txt: str) -> str:
        return " ".join(str(txt or "").replace("\r", " ").replace("\n", " ").split()).strip().lower()

    def _slot_key(txt: str) -> str:
        n = _norm(txt)
        parts = n.split(" ")
        if len(parts) >= 2:
            return f"{parts[0]} {parts[1]}"
        return n

    remaining = list(range(len(original_labels)))
    original_norm = [_norm(x) for x in original_labels]
    original_slot = [_slot_key(x) for x in original_labels]

    mapped: list[dict] = []
    for lbl in sorted_labels:
        lbl_norm = _norm(lbl)
        lbl_slot = _slot_key(lbl)

        found_pos = next((pos for pos, idx in enumerate(remaining) if original_norm[idx] == lbl_norm), None)
        if found_pos is None:
            found_pos = next((pos for pos, idx in enumerate(remaining) if original_slot[idx] == lbl_slot), None)
        if found_pos is None:
            continue

        original_idx = remaining.pop(found_pos)
        mapped.append(dict(original_days[original_idx]))

    return mapped if len(mapped) == len(original_days) else [dict(d) for d in original_days]


def _normalizar_txt_fuerza(txt: str) -> str:
    t = str(txt or "").lower().strip()
    return (
        t.replace("á", "a").replace("é", "e").replace("í", "i")
         .replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    )


def _grupo_fuerza_desde_tipo(tipo: str) -> str | None:
    t = _normalizar_txt_fuerza(tipo)
    if "pull" in t:
        return "Pull"
    if "push" in t:
        return "Push"
    if "pierna" in t:
        return "Pierna"
    return None


def _nota_bloquea_subida(nota: str) -> bool:
    n = _normalizar_txt_fuerza(nota)
    return "sint" in n or "sin t" in n or "sintecnica" in n


def _ejercicio_en_grupo_fuerza(grupo_dia: str, ejercicio: str, grupo: str, musculo: str) -> bool:
    txt = " ".join([
        _normalizar_txt_fuerza(ejercicio),
        _normalizar_txt_fuerza(grupo),
        _normalizar_txt_fuerza(musculo),
    ])
    pull_keys = ["espalda", "bicep", "dorsal", "trapecio", "remo", "jalon", "dominada", "curl"]
    push_keys = ["pecho", "hombro", "tricep", "deltoid", "press", "fondo", "apertura"]
    leg_keys = ["pierna", "cuadricep", "isquio", "gluteo", "femoral", "gemelo", "sentadilla", "hip thrust", "zancada", "prensa"]

    if grupo_dia == "Pull":
        return any(k in txt for k in pull_keys)
    if grupo_dia == "Push":
        return any(k in txt for k in push_keys) and not any(k in txt for k in leg_keys)
    if grupo_dia == "Pierna":
        return any(k in txt for k in leg_keys)
    return False


def _recomendaciones_progresion_grupo(usuario_id: int, grupo_dia: str) -> list[str]:
    """
    Recomendaciones generales de progresion para el grupo del dia.
    Regla solicitada:
    - Nota con "sinT" => no recomendar subir en ese ejercicio.
    - Nota vacia => recomendar subida de peso.
    """
    conn = get_db_connection()
    try:
        rows = conn.execute(
            """SELECT e.ejercicio, e.series, e.repeticiones, e.peso, e.sensaciones,
                      e.grupo_muscular, e.musculo_principal, s.fecha, e.id
               FROM ejercicios_fuerza e
               JOIN sesiones_fuerza s ON s.id = e.sesion_id
               WHERE s.usuario_id=?
               ORDER BY s.fecha DESC, e.id DESC""",
            (usuario_id,),
        ).fetchall()
    except Exception:
        rows = []
    finally:
        conn.close()

    ultimo_por_ej = {}
    for r in rows:
        nombre = str(r[0] or "").strip()
        if not nombre:
            continue
        key = _normalizar_txt_fuerza(nombre)
        if key not in ultimo_por_ej:
            ultimo_por_ej[key] = r

    recomendaciones = []
    for r in ultimo_por_ej.values():
        nombre = str(r[0] or "").strip()
        series = int(r[1] or 0)
        reps = int(r[2] or 0)
        peso = float(r[3] or 0)
        nota = str(r[4] or "").strip()
        grupo = str(r[5] or "")
        musculo = str(r[6] or "")

        if not _ejercicio_en_grupo_fuerza(grupo_dia, nombre, grupo, musculo):
            continue
        if _nota_bloquea_subida(nota):
            continue
        if nota:
            continue

        peso_txt = f"{peso:g}kg" if peso > 0 else "peso corporal"
        recomendaciones.append(
            f"Subir peso en {nombre} (ultimo: {series}x{reps} {peso_txt} sin nota)."
        )

    return sorted(recomendaciones)


def _normalizar_dias_semana(dias: list[dict]) -> list[dict]:
    """Garantiza una sola sesión por fecha para que KPI/UI sean coherentes (7 días)."""
    if not dias:
        return []

    por_fecha = {}

    def _score(d: dict) -> tuple:
        tipo = str(d.get("tipo", ""))
        es_descanso = 1 if tipo == "Descanso" else 0
        es_fuerza = 1 if (tipo in _TIPOS_FUERZA or "Fuerza" in tipo) else 0
        km = float(d.get("km") or 0)
        dur = float(d.get("duracion_min") or 0)
        # Preferimos no-descanso, luego más carga total, luego fuerza.
        return (es_descanso, -(km + dur / 60.0), -es_fuerza)

    for d in dias:
        fecha = str(d.get("fecha", ""))[:10]
        if not fecha:
            continue
        actual = por_fecha.get(fecha)
        if actual is None or _score(d) < _score(actual):
            por_fecha[fecha] = d

    return [por_fecha[f] for f in sorted(por_fecha.keys())]

# ---------------------------------------------------------------------------
# Estado
# ---------------------------------------------------------------------------
if "plan_last_user" not in st.session_state:
    st.session_state["plan_last_user"] = user_actual
elif st.session_state["plan_last_user"] != user_actual:
    for _k in ("plan_cursor", "plan_data", "plan_ia", "plan_dia_sel"):
        st.session_state.pop(_k, None)
    st.session_state["plan_last_user"] = user_actual

if "plan_cursor" not in st.session_state:
    st.session_state.plan_cursor = _lunes_de(datetime.now())
if "plan_data" not in st.session_state:
    st.session_state.plan_data = None
if "plan_ia" not in st.session_state:
    st.session_state.plan_ia = True
if "plan_dia_sel" not in st.session_state:
    st.session_state.plan_dia_sel = 0
if "plan_add_session_day" not in st.session_state:
    st.session_state["plan_add_session_day"] = None

lunes = st.session_state.plan_cursor
if st.session_state.plan_data is None:
    plan_bd = _cargar_plan_de_bd(user_actual, lunes)
    if plan_bd:
        st.session_state.plan_data = plan_bd
        st.session_state.plan_ia = False

# ---------------------------------------------------------------------------
# TAB STATE & NAVIGATION
# ---------------------------------------------------------------------------
active_tab = st.session_state.get("plan_active_tab", "generar")

# ============================================================================
# TAB 1: GENERAR PLAN
# ============================================================================
if active_tab == "generar":

    # Compact controls: previous week, current week label, next week, regenerate.
    nav_c1, nav_c2, nav_c3, nav_c4 = st.columns([0.13, 0.45, 0.13, 0.29], gap="small")
    with nav_c1:
        if st.button("⬅️", key="plan_prev", use_container_width=True, help="Semana anterior"):
            st.session_state.plan_cursor -= timedelta(weeks=1)
            st.session_state.plan_data = None; st.rerun()
    with nav_c2:
        st.markdown(
            f"""
            <div style="
                height:100%;
                min-height:46px;
                display:flex;
                align-items:center;
                justify-content:center;
                border-radius:12px;
                border:1px solid rgba(0,212,255,0.2);
                background:linear-gradient(135deg, rgba(15,23,36,0.95), rgba(16,25,40,0.95));
                color:#E6F3FF;
                font-size:1rem;
                font-weight:800;
                letter-spacing:0.01em;
            ">{_rango_semana_es(st.session_state.plan_cursor)}</div>
            """,
            unsafe_allow_html=True,
        )
    with nav_c3:
        if st.button("➡️", key="plan_next", use_container_width=True, help="Semana siguiente"):
            st.session_state.plan_cursor += timedelta(weeks=1)
            st.session_state.plan_data = None; st.rerun()
    with nav_c4:
        _spacer, right_controls = st.columns([0.22, 0.78], gap="small")
        with right_controls:
            sin_col, regen_col = st.columns([0.42, 0.58], gap="small")
            with sin_col:
                sin_ia = st.checkbox("Sin IA", key="plan_sin_ia")
                if sin_ia:
                    st.session_state.plan_ia = False
            with regen_col:
                if st.button("⚡ Regenerar", type="primary", use_container_width=True, key="plan_generate_small"):
                    with st.spinner("Generando plan..."):
                        try:
                            from src.plan.entrenador import generar_entrenamiento_semana
                            plan_nuevo = generar_entrenamiento_semana(user_actual, lunes)

                            # DEBUG: mostrar tipos generados
                            tipos_gen = [d.get("tipo", "?") for d in plan_nuevo.get("dias", [])]
                            if not any(t not in ("Regenerativo", "Descanso", "Movilidad") for t in tipos_gen):
                                st.warning(f"⚠️ Aviso: Plan generado solo con tipos: {tipos_gen}. Revisando...")

                            plan_nuevo = _adaptar_plan_a_hoy(plan_nuevo, user_actual, lunes, datetime.now())
                            st.session_state.plan_data = plan_nuevo
                            st.session_state.plan_ia = True
                            _auto_guardar(user_actual, lunes, plan_nuevo)
                        except Exception as e:
                            st.error(f"❌ Error generando plan:\n\n{str(e)}")
                            import traceback
                            st.error(f"**Traceback completo:**\n\n```\n{traceback.format_exc()}\n```")
                            st.stop()
                    st.rerun()

    st.markdown(
        """
        <div style='height:1rem;'></div>
        <div style='height:1px;background:linear-gradient(90deg,rgba(0,212,255,0.0),rgba(0,212,255,0.28),rgba(201,255,0,0.22),rgba(0,212,255,0.28),rgba(0,212,255,0.0));'></div>
        <div style='height:1.8rem;'></div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.plan_data is None:
        st.info("Pulsa **⚡ Regenerar** para generar el plan de esta semana con IA personalizada.")
        st.stop()

    plan = st.session_state.plan_data
    if not isinstance(plan, dict) or "fase" not in plan:
        plan_bd = _cargar_plan_de_bd(user_actual, lunes)
        if plan_bd and isinstance(plan_bd, dict) and "fase" in plan_bd:
            st.session_state.plan_data = plan_bd
            st.rerun()
        st.error("Error: El plan no contiene datos válidos. Intenta regenerarlo.")
        st.stop()

    # Normalizamos por fecha para evitar inflar KPIs cuando hay sesiones duplicadas en BD.
    plan["dias"] = _normalizar_dias_semana(plan.get("dias", []))
    st.session_state.plan_data = plan

    fase = plan["fase"]
    semaforo = plan["semaforo"]

    dias_plan = plan.get("dias", [])
    km_totales = round(sum(float(d.get("km") or 0) for d in dias_plan), 1)
    km_hechos_semana = _km_hechos_semana(user_actual, lunes)
    sesiones_no_descanso = len([d for d in dias_plan if d.get("tipo") != "Descanso"])
    fuerza_count = len([d for d in dias_plan if d.get("tipo") in _TIPOS_FUERZA or "Fuerza" in str(d.get("tipo", ""))])
    fase_nombre = fase.get("fase_nombre", "—")

    # ── Hero Banner ──────────────────────────────────────────────────────────
    _perfil_plan = {}
    try:
        from src.db.db_manager import obtener_perfil as _op
        _perfil_plan = _op(user_actual) or {}
    except Exception:
        pass
    _fecha_obj_hero = _perfil_plan.get("fecha_objetivo") or _perfil_plan.get("fecha_objetivo_primario")
    _obj_nombre_hero = _perfil_plan.get("objetivo_primario") or _perfil_plan.get("objetivo_tipo") or "Objetivo"
    _dias_obj_hero = ""
    if _fecha_obj_hero:
        try:
            _fobj = datetime.strptime(str(_fecha_obj_hero), "%Y-%m-%d")
            _d = (_fobj - datetime.now()).days
            if _d > 0:
                _dias_obj_hero = f" · {_d} días para {_obj_nombre_hero}"
        except Exception:
            pass
    _semana_label = _rango_semana_es(lunes)
    _semaforo_color_map = {"verde": "#22c55e", "ambar": "#f59e0b", "rojo": "#ef4444"}
    _sem_color = _semaforo_color_map.get(semaforo.get("color", "ambar"), "#f59e0b")
    _sem_dot = f"<span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:{_sem_color};margin-right:5px;box-shadow:0 0 6px {_sem_color};'></span>"

    st.markdown(f"""
<div style="
    background:linear-gradient(135deg,rgba(0,212,255,0.12) 0%,rgba(34,197,94,0.06) 52%,rgba(168,85,247,0.1) 100%);
    border:1px solid rgba(0,212,255,0.22);
    border-radius:18px;padding:1.4rem 1.6rem;margin-bottom:1.2rem;position:relative;overflow:hidden;
">
  <div style="position:absolute;top:-30px;right:-30px;width:180px;height:180px;border-radius:50%;
    background:radial-gradient(circle,rgba(0,212,255,0.12),transparent);pointer-events:none;"></div>
  <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.5rem;">
    <span style="background:rgba(0,212,255,0.15);color:#67e8f9;font-size:.7rem;font-weight:700;
      padding:3px 10px;border-radius:20px;border:1px solid rgba(0,212,255,0.3);">{fase_nombre}</span>
    <span style="background:rgba(34,197,94,0.15);color:#86efac;font-size:.7rem;font-weight:700;
      padding:3px 10px;border-radius:20px;border:1px solid rgba(34,197,94,0.3);">
      {_sem_dot}Semáforo: {semaforo.get("color","—").capitalize()}</span>
  </div>
  <h2 style="color:white;font-size:1.35rem;font-weight:800;margin:0 0 .3rem;">
    Plan Semanal — {_semana_label}</h2>
  <p style="color:#8B949E;font-size:.82rem;margin:0;">{km_totales} km objetivo esta semana{_dias_obj_hero}</p>
</div>""", unsafe_allow_html=True)

    # ── KPI Cards ────────────────────────────────────────────────────────────
    kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4, gap="medium")

    _kpi_card(kpi_c1, "🏃", "KM Semana", f"{km_hechos_semana:.1f}/{km_totales:.1f}", "#00D4FF", "rgba(0,212,255,0.1)", "rgba(0,212,255,0.25)")
    _kpi_card(kpi_c2, "📋", "Sesiones", str(sesiones_no_descanso), "#4ade80", "rgba(74,222,128,0.1)", "rgba(74,222,128,0.25)")
    _kpi_card(kpi_c3, "💪", "Fuerza", str(fuerza_count), "#c084fc", "rgba(192,132,252,0.1)", "rgba(192,132,252,0.25)")
    _kpi_card(kpi_c4, "📍", "Fase", fase_nombre, "#f97316", "rgba(249,115,22,0.1)", "rgba(249,115,22,0.25)")

    st.markdown("<div style='height:1.35rem;'></div>", unsafe_allow_html=True)

    # "Distribución Semanal" heading
    st.markdown("""
<div style="display:flex;align-items:center;gap:0.5rem;margin:1.5rem 0 1rem;">
  <span style="color:#C9FF00;font-size:1rem;">📅</span>
  <span style="font-size:0.85rem;font-weight:700;color:white;text-transform:uppercase;letter-spacing:.07em;">Distribución Semanal</span>
  <div style="flex:1;height:1px;background:linear-gradient(90deg,rgba(201,255,0,0.3),transparent);margin-left:.5rem;"></div>
</div>""", unsafe_allow_html=True)

    dias_plan = plan.get("dias", [])

    # Inicializa selección del día (hoy si existe, si no lunes)
    hoy_str = datetime.now().strftime("%Y-%m-%d")
    idx_hoy = next((idx for idx, d in enumerate(dias_plan) if d.get("fecha") == hoy_str), 0)
    if "plan_selected_day_idx" not in st.session_state:
        st.session_state["plan_selected_day_idx"] = idx_hoy
    elif st.session_state["plan_selected_day_idx"] is None:
        st.session_state["plan_selected_day_idx"] = idx_hoy
    elif st.session_state["plan_selected_day_idx"] >= len(dias_plan):
        st.session_state["plan_selected_day_idx"] = 0

    if dias_plan:
        # Garantiza calendario fijo de 7 días.
        if len(dias_plan) != 7:
            dias_plan = _reaplicar_slots_semana(dias_plan[:7], lunes)
            while len(dias_plan) < 7:
                idx = len(dias_plan)
                dias_plan.append({
                    "fecha": (lunes + timedelta(days=idx)).strftime("%Y-%m-%d"),
                    "dia": _DIA_CORTO[idx],
                    "tipo": "Descanso",
                    "km": 0,
                    "duracion_min": 0,
                    "intensidad": "—",
                    "descripcion_ia": "",
                    "alerta": "",
                })
            plan["dias"] = dias_plan
            st.session_state.plan_data = plan
            _auto_guardar(user_actual, lunes, plan)

        week_key = lunes.strftime("%Y%m%d")
        board_key = f"plan_session_board_{week_key}"

        # Inicializa tablero: 7 columnas (una por día), cada columna admite varias sesiones.
        if board_key not in st.session_state:
            board_saved = plan.get("board_sesiones") if isinstance(plan.get("board_sesiones"), list) else None
            if board_saved and len(board_saved) == 7:
                st.session_state[board_key] = board_saved
            else:
                board_init = []
                for d in dias_plan:
                    board_init.append([{
                        "tipo": d.get("tipo", "Descanso"),
                        "km": float(d.get("km") or 0),
                        "duracion_min": float(d.get("duracion_min") or 0),
                        "intensidad": d.get("intensidad", "—"),
                        "descripcion_ia": d.get("descripcion_ia", ""),
                        "alerta": d.get("alerta", ""),
                    }])
                st.session_state[board_key] = board_init

        board = st.session_state[board_key]

        # ── Procesar drop de DnD recibido vía query param ────────────────────
        import json as _json
        _dnd_param = st.query_params.get("dnd_move", "")
        if _dnd_param:
            try:
                _mv = _json.loads(_dnd_param)
                _fd, _fi, _td = int(_mv["from_day"]), int(_mv["from_idx"]), int(_mv["to_day"])
                if _fd != _td and 0 <= _fd < 7 and 0 <= _td < 7 and 0 <= _fi < len(board[_fd]):
                    _ses_mv = board[_fd].pop(_fi)
                    board[_td].append(_ses_mv)
                    st.session_state[board_key] = board
            except Exception:
                pass
            st.query_params.clear()
            st.rerun()

        def _sync_plan_from_board(persist: bool = True) -> None:
            nuevas = []
            for idx in range(7):
                fecha = (lunes + timedelta(days=idx)).strftime("%Y-%m-%d")
                sesiones = board[idx] if idx < len(board) else []
                if sesiones:
                    principal = dict(sesiones[0])
                    principal["fecha"] = fecha
                    principal["dia"] = _DIA_CORTO[idx]
                    principal["sesiones_extra"] = [dict(x) for x in sesiones[1:]]
                    nuevas.append(principal)
                else:
                    nuevas.append({
                        "fecha": fecha,
                        "dia": _DIA_CORTO[idx],
                        "tipo": "Descanso",
                        "km": 0,
                        "duracion_min": 0,
                        "intensidad": "—",
                        "descripcion_ia": "",
                        "alerta": "",
                        "sesiones_extra": [],
                    })
            plan["dias"] = nuevas
            plan["board_sesiones"] = board
            st.session_state.plan_data = plan
            if persist:
                _auto_guardar(user_actual, lunes, plan)

        # ── Colores por tipo de actividad ─────────────────────────────────────
        _BORDER_COLOR = {
            "running":  "#22d3ee",
            "strength": "#c084fc",
            "rest":     "#4ade80",
            "default":  "#C9FF00",
        }

        # ── Construir JSON del tablero para el componente HTML ────────────────
        _board_js = []
        _max_items = 0
        for _bi in range(7):
            _fecha_dt = lunes + timedelta(days=_bi)
            _is_today = _fecha_dt.strftime("%Y-%m-%d") == datetime.now().strftime("%Y-%m-%d")
            _items_js = []
            for _si, _ses in enumerate(board[_bi]):
                _tipo  = str(_ses.get("tipo") or "Descanso")
                _emoji = _EMOJIS.get(_tipo, "📅")
                _km    = float(_ses.get("km") or 0)
                _dur   = float(_ses.get("duracion_min") or 0)
                _int   = str(_ses.get("intensidad") or "").strip()
                _act   = _get_activity_type(_tipo)
                _col   = _BORDER_COLOR.get(_act, _BORDER_COLOR["default"])
                if _act == "running" and _km > 0 and _dur > 0:
                    _carga = f"{_km:.1f} km · {int(_dur)} min"
                elif _km > 0:
                    _carga = f"{_km:.1f} km"
                elif _dur > 0:
                    _carga = f"{int(_dur)} min"
                else:
                    _carga = "—"
                _items_js.append({
                    "label": _tipo, "emoji": _emoji, "carga": _carga,
                    "int": _int, "color": _col, "day": _bi, "idx": _si
                })
            _board_js.append({
                "header": _DIA_CORTO[_bi],
                "date": f"{_fecha_dt.day} {_fecha_dt.strftime('%b')}",
                "today": _is_today,
                "items": _items_js,
            })
            _max_items = max(_max_items, len(_items_js))

        _bj      = _json.dumps(_board_js, ensure_ascii=False)
        _comp_h  = max(120, _max_items * 68 + 80)

        _dnd_html = f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:transparent;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;overflow:hidden}}
.board{{display:flex;gap:8px;width:100%;height:100%}}
.day-col{{
  flex:1;min-width:0;
  background:rgba(14,17,23,0.97);
  border:1px solid rgba(255,255,255,0.07);
  border-radius:12px;overflow:hidden;
  display:flex;flex-direction:column;
  transition:border-color .15s,background .15s,box-shadow .15s
}}
.day-col.today{{border-color:rgba(201,255,0,0.3);}}
.day-col.over{{
  border-color:rgba(201,255,0,0.6)!important;
  background:rgba(15,28,15,0.98)!important;
  box-shadow:0 0 0 1px rgba(201,255,0,0.2),0 4px 20px rgba(201,255,0,0.08)!important
}}
.day-header{{
  padding:8px 10px 6px;
  border-bottom:1px solid rgba(255,255,255,0.05);
  flex-shrink:0
}}
.day-name{{font-size:9px;color:#6b7280;font-weight:800;text-transform:uppercase;letter-spacing:.08em;line-height:1}}
.day-date{{font-size:11px;color:#c8d1d9;font-weight:700;margin-top:2px;line-height:1}}
.today-dot{{display:inline-block;width:5px;height:5px;border-radius:50%;background:#C9FF00;margin-left:4px;vertical-align:middle}}
.day-body{{padding:6px;flex:1;min-height:32px}}
.empty-day{{text-align:center;padding:10px 4px;color:#374151;font-size:9px;font-weight:600;letter-spacing:.05em;text-transform:uppercase}}
.ses{{
  border:1px solid rgba(255,255,255,0.06);
  border-radius:9px;padding:6px 8px;
  margin-bottom:4px;cursor:grab;
  background:rgba(22,27,34,0.95);
  user-select:none;
  transition:opacity .12s,border-color .15s,background .15s,transform .1s
}}
.ses:hover{{border-color:rgba(201,255,0,0.3);background:rgba(30,40,55,0.98);transform:translateY(-1px)}}
.ses.dragging{{opacity:.2;cursor:grabbing;transform:scale(.97)}}
.ses-top{{display:flex;align-items:center;gap:5px;margin-bottom:2px}}
.ses-dot{{width:7px;height:7px;border-radius:50%;flex-shrink:0}}
.ses-name{{font-size:10px;font-weight:700;color:#e5e7eb;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.ses-sub{{font-size:9px;color:#6b7280;line-height:1.2;padding-left:12px}}
.ses-int{{
  display:inline-block;font-size:8px;font-weight:700;
  padding:1px 5px;border-radius:10px;
  color:inherit;border:1px solid currentColor;opacity:.75;margin-top:3px
}}
</style></head><body>
<div class="board" id="board"></div>
<script>
const B={_bj};
let src=null;
function build(){{
  const el=document.getElementById('board');
  el.innerHTML='';
  B.forEach((day,di)=>{{
    const col=document.createElement('div');
    col.className='day-col'+(day.today?' today':'');

    // Header
    const hdr=document.createElement('div');
    hdr.className='day-header';
    const nm=document.createElement('div');nm.className='day-name';nm.textContent=day.header;
    if(day.today){{const dot=document.createElement('span');dot.className='today-dot';nm.appendChild(dot);}}
    const dt=document.createElement('div');dt.className='day-date';dt.textContent=day.date;
    hdr.appendChild(nm);hdr.appendChild(dt);col.appendChild(hdr);

    // Body (drop zone)
    const body=document.createElement('div');body.className='day-body';body.dataset.di=di;
    body.addEventListener('dragover',e=>{{e.preventDefault();col.classList.add('over')}});
    body.addEventListener('dragleave',e=>{{if(!col.contains(e.relatedTarget))col.classList.remove('over')}});
    body.addEventListener('drop',e=>{{
      e.preventDefault();col.classList.remove('over');
      if(!src||src.di===di)return;
      const mv=JSON.stringify({{from_day:src.di,from_idx:src.ii,to_day:di}});
      window.parent.location.search='?dnd_move='+encodeURIComponent(mv);
    }});

    if(day.items.length===0){{
      const empty=document.createElement('div');
      empty.className='empty-day';empty.textContent='descanso';
      body.appendChild(empty);
    }}

    day.items.forEach((item,ii)=>{{
      const s=document.createElement('div');s.className='ses';s.draggable=true;
      // Top row: dot + name
      const top=document.createElement('div');top.className='ses-top';
      const dot=document.createElement('span');dot.className='ses-dot';dot.style.background=item.color;
      const name=document.createElement('span');name.className='ses-name';
      name.style.color=item.color;name.textContent=item.emoji+' '+item.label;
      top.appendChild(dot);top.appendChild(name);s.appendChild(top);
      // Sub row: carga
      const sub=document.createElement('div');sub.className='ses-sub';
      sub.textContent=item.carga;
      if(item.int&&item.int!=='—'){{
        const badge=document.createElement('span');badge.className='ses-int';
        badge.style.color=item.color;badge.style.borderColor=item.color;
        badge.textContent=item.int;sub.appendChild(document.createElement('br'));sub.appendChild(badge);
      }}
      s.appendChild(sub);
      s.addEventListener('dragstart',e=>{{
        src={{di,ii}};s.classList.add('dragging');
        e.dataTransfer.effectAllowed='move';
      }});
      s.addEventListener('dragend',()=>{{
        s.classList.remove('dragging');src=null;
        document.querySelectorAll('.day-col').forEach(c=>c.classList.remove('over'));
      }});
      body.appendChild(s);
    }});
    col.appendChild(body);
    el.appendChild(col);
  }});
}}
build();
</script></body></html>"""

        st.components.v1.html(_dnd_html, height=_comp_h, scrolling=False)

        # ── Fila de botones por día (compacta, bajo el tablero) ───────────────
        btn_cols = st.columns(7, gap="small")
        for i in range(7):
            is_selected = st.session_state.get("plan_selected_day_idx") == i
            is_adding   = st.session_state.get("plan_add_session_day") == i
            with btn_cols[i]:
                bc1, bc2 = st.columns([3, 1], gap="small")
                with bc1:
                    lbl = "▼" if is_selected else "···"
                    if st.button(lbl, key=f"plan_day_sel_{i}",
                                 use_container_width=True,
                                 type="primary" if is_selected else "secondary"):
                        st.session_state["plan_selected_day_idx"] = None if is_selected else i
                        st.session_state["plan_add_session_day"]  = None
                        st.rerun()
                with bc2:
                    if st.button("＋", key=f"plan_day_add_{i}",
                                 use_container_width=True,
                                 type="primary" if is_adding else "secondary",
                                 help="Añadir sesión"):
                        st.session_state["plan_add_session_day"] = None if is_adding else i
                        st.rerun()

        # Mantener estructura de plan sincronizada con el tablero en memoria (sin guardar cada render).
        _sync_plan_from_board(persist=False)
        dias_plan = plan.get("dias", dias_plan)

        # ── Formulario para añadir nueva sesión ─────────────────────────────
        add_day_idx = st.session_state.get("plan_add_session_day")
        if add_day_idx is not None and 0 <= add_day_idx < 7:
            add_fecha = (lunes + timedelta(days=add_day_idx)).strftime("%Y-%m-%d")
            add_label = _DIA_CORTO[add_day_idx]
            st.markdown(f"""
<div style="background:rgba(14,17,23,0.97);border:1px solid rgba(201,255,0,0.25);
  border-radius:14px;padding:1rem 1.2rem;margin-top:1rem;">
  <div style="display:flex;align-items:center;gap:.6rem;margin-bottom:.8rem;">
    <span style="color:#C9FF00;font-size:.95rem;">➕</span>
    <span style="color:white;font-size:.9rem;font-weight:700;">Nueva sesión — {add_label}</span>
    <span style="color:#8B949E;font-size:.78rem;">{add_fecha}</span>
  </div>
</div>""", unsafe_allow_html=True)

            _todos_tipos = sorted(list(_TIPOS_CARRERA) + list(_TIPOS_FUERZA) + ["Descanso", "Movilidad"])
            af1, af2, af3 = st.columns([2, 1, 1], gap="small")
            with af1:
                new_tipo = st.selectbox("Tipo de sesión", _todos_tipos,
                                        key=f"add_tipo_{add_day_idx}", label_visibility="collapsed")
            with af2:
                new_dur = st.number_input("Min", min_value=0, max_value=300, value=45, step=5,
                                          key=f"add_dur_{add_day_idx}", label_visibility="collapsed")
            with af3:
                new_km = st.number_input("KM", min_value=0.0, max_value=100.0, value=0.0, step=0.5,
                                         key=f"add_km_{add_day_idx}", label_visibility="collapsed", format="%.1f")

            af4, af5, af6 = st.columns([2, 1, 1], gap="small")
            with af4:
                new_int = st.text_input("Intensidad", value="Media", key=f"add_int_{add_day_idx}",
                                        label_visibility="collapsed", placeholder="Ej: Baja / Media / Alta")
            with af5:
                if st.button("✅ Añadir", key=f"add_confirm_{add_day_idx}", use_container_width=True, type="primary"):
                    nueva_ses = {
                        "tipo": new_tipo,
                        "km": new_km,
                        "duracion_min": new_dur,
                        "intensidad": new_int or "Media",
                        "descripcion_ia": "",
                        "alerta": "",
                    }
                    board[add_day_idx].append(nueva_ses)
                    st.session_state[board_key] = board
                    _sync_plan_from_board(persist=True)
                    st.session_state["plan_add_session_day"] = None
                    st.rerun()
            with af6:
                if st.button("✕ Cancelar", key=f"add_cancel_{add_day_idx}", use_container_width=True):
                    st.session_state["plan_add_session_day"] = None
                    st.rerun()

    # ── Panel de detalle del día seleccionado ───────────────────────────────
    selected_idx = st.session_state.get("plan_selected_day_idx")
    if selected_idx is not None and selected_idx < len(dias_plan):
        dia = dias_plan[selected_idx]
        tipo = dia["tipo"]
        act_type_det = _get_activity_type(tipo)
        color_det = _TYPE_COLORS.get(act_type_det, _TYPE_COLORS["default"])
        type_label = {"running": "Carrera", "strength": "Fuerza", "rest": "Descanso"}.get(act_type_det, tipo)
        _badge_bg_det = {"running": "rgba(34,211,238,0.15)", "strength": "rgba(192,132,252,0.15)", "rest": "rgba(74,222,128,0.15)"}.get(act_type_det, "rgba(255,255,255,0.08)")
        _badge_border_det = {"running": "rgba(34,211,238,0.4)", "strength": "rgba(192,132,252,0.4)", "rest": "rgba(74,222,128,0.4)"}.get(act_type_det, "rgba(255,255,255,0.15)")

        st.markdown(f"""
<div style="background:rgba(14,17,23,0.97);border:1px solid rgba(201,255,0,0.2);
border-radius:16px;overflow:hidden;margin-top:1.2rem;">
  <div style="display:flex;align-items:center;justify-content:space-between;
    padding:1rem 1.25rem;border-bottom:1px solid rgba(255,255,255,0.06);">
    <div style="display:flex;align-items:center;gap:.75rem;">
      <div style="width:4px;height:40px;border-radius:4px;background:{color_det};
        box-shadow:0 0 8px {color_det}88;"></div>
      <div>
        <div style="display:flex;align-items:center;gap:.5rem;">
          <span style="color:white;font-size:1rem;font-weight:800;">{escape(tipo)}</span>
          <span style="font-size:.7rem;font-weight:700;padding:2px 9px;border-radius:20px;
            background:{_badge_bg_det};border:1px solid {_badge_border_det};color:{color_det};">{type_label}</span>
        </div>
        <p style="color:#8B949E;font-size:.75rem;margin:.2rem 0 0;">{dia.get('dia','—')} · {dia.get('fecha','')} · {int(dia.get('duracion_min') or 0)} min</p>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

        if tipo in _TIPOS_FUERZA or "Fuerza" in tipo:
            grupo_dia = _grupo_fuerza_desde_tipo(tipo)
            protocolo = str(dia.get("alerta") or "").strip()

            st.markdown(
                "<p style='color:#8B949E;font-size:.74rem;font-weight:700;"
                "text-transform:uppercase;letter-spacing:.07em;margin:.6rem 0 .45rem;'>"
                "Recomendaciones Generales de Fuerza</p>",
                unsafe_allow_html=True,
            )

            if protocolo:
                st.markdown(
                    f"<div style='background:rgba(34,58,94,0.22);border:1px solid rgba(96,165,250,0.35);"
                    f"border-radius:10px;padding:.55rem .75rem;margin-bottom:.55rem;color:#bfdbfe;font-size:.8rem;'>"
                    f"{escape(protocolo)}</div>",
                    unsafe_allow_html=True,
                )

            recs = _recomendaciones_progresion_grupo(user_actual, grupo_dia) if grupo_dia else []
            if recs:
                for rec in recs[:8]:
                    st.markdown(
                        f"<div style='background:rgba(22,27,34,0.9);border:1px solid rgba(255,255,255,0.07);"
                        f"border-radius:10px;padding:.5rem .75rem;margin-bottom:.35rem;color:#e5e7eb;font-size:.82rem;'>"
                        f"• {escape(rec)}</div>",
                        unsafe_allow_html=True,
                    )
            elif grupo_dia:
                st.caption(
                    f"Para {grupo_dia} no hay subidas de peso pendientes con tus ultimos registros. "
                    "Si un ejercicio lleva nota sinT, se omite automaticamente de recomendaciones."
                )
            else:
                st.caption("Sesion de fuerza general. Se aplican solo recomendaciones de protocolo.")

        elif tipo in _TIPOS_CARRERA:
            from src.garmin.workout_builder import sesion_a_bloques
            bloques = sesion_a_bloques(dia)
            st.markdown(html_detalle_carrera(dia, bloques), unsafe_allow_html=True)
        else:
            st.markdown(html_detalle_descanso(dia), unsafe_allow_html=True)

        if st.session_state.get("plan_ia") and dia.get("descripcion_ia"):
            st.markdown(
                f"<div style='background:#0f1e10;border-left:3px solid #a3e635;border-radius:0 8px 8px 0;"
                f"padding:10px 14px;margin:8px 0;font-size:12px;color:#c9d1d9;'>"
                f"<span style='font-size:10px;color:#a3e635;text-transform:uppercase;letter-spacing:0.6px;"
                f"font-weight:700;'>🤖 Entrenador IA</span><br><br>"
                f"{dia['descripcion_ia']}</div>",
                unsafe_allow_html=True)

        ajuste = st.text_area(
            "Ajuste",
            placeholder="Ej: reducir 3km, cambiar a Z1 todo...",
            height=68,
            key=f"ajuste_{selected_idx}",
            label_visibility="collapsed",
        )
        if st.button("Aplicar cambio", key=f"ajuste_btn_{selected_idx}"):
            plan["dias"][selected_idx]["alerta"] = f"[Ajuste] {ajuste}"
            st.session_state.plan_data = plan
            st.success("Cambio anotado.")
            st.rerun()

    recomendaciones_semana = []
    vistos = set()

    for a in plan.get("alertas", []):
        texto = str(a or "").strip()
        clave = texto.lower()
        if texto and clave not in vistos:
            recomendaciones_semana.append(texto)
            vistos.add(clave)

    if st.session_state.get("plan_ia"):
        for d in plan.get("dias", []):
            desc_ia = str(d.get("descripcion_ia") or "").strip()
            if not desc_ia:
                continue
            dia_lbl = str(d.get("dia") or "Sesion")
            tipo_lbl = str(d.get("tipo") or "Entrenamiento")
            texto = f"{tipo_lbl} ({dia_lbl}) — {desc_ia}"
            clave = texto.lower()
            if clave not in vistos:
                recomendaciones_semana.append(texto)
                vistos.add(clave)

    if recomendaciones_semana:
        filas_html = []
        for rec in recomendaciones_semana:
            icono, titulo, descripcion = _descomponer_recomendacion(rec)
            color_titulo, fondo = _estilo_recomendacion(rec)
            descripcion_html = (
                f"<p style='color:#8B949E;font-size:.74rem;line-height:1.4;margin:.2rem 0 0 0;'>{escape(descripcion)}</p>"
                if descripcion else ""
            )
            filas_html.append(
                f"""
<div style="display:flex;align-items:flex-start;gap:.7rem;padding:.72rem .8rem;border-radius:12px;
background:{fondo};border:1px solid rgba(255,255,255,0.06);margin-bottom:.55rem;">
  <span style="font-size:1rem;line-height:1.1;">{escape(icono)}</span>
  <div style="min-width:0;">
    <p style="margin:0;color:{color_titulo};font-size:.81rem;font-weight:700;line-height:1.3;">{escape(titulo)}</p>
    {descripcion_html}
  </div>
</div>"""
            )

        st.markdown(
            f"""
<div style="background:linear-gradient(135deg,rgba(168,85,247,0.09),rgba(0,212,255,0.05));
border:1px solid rgba(168,85,247,0.24);border-radius:16px;padding:1rem 1rem .95rem;margin:1.2rem 0 0 0;">
  <div style="display:flex;align-items:center;gap:.5rem;color:#ffffff;font-size:.88rem;font-weight:700;margin:0 0 .7rem 0;">
    <span style="color:#c084fc;">✨</span>
    Recomendaciones IA para esta semana
  </div>
  {''.join(filas_html)}
</div>""",
            unsafe_allow_html=True,
        )

    # Guardar
    st.divider()
    if st.button("💾 Guardar plan en BD", type="primary", use_container_width=True):
        conn = get_db_connection(); semana_str = lunes.strftime("%Y-%m-%d")
        try:
            conn.execute("DELETE FROM plan_entrenamiento WHERE usuario_id=? AND semana_inicio=?",
                         (user_actual, semana_str))
            for d in plan["dias"]:
                desc = d.get("descripcion_ia") or d.get("alerta","")
                conn.execute(
                    "INSERT INTO plan_entrenamiento (usuario_id,semana_inicio,fecha,tipo,sesion,duracion_min,intensidad,creado_en) "
                    "VALUES (?,?,?,?,?,?,?,?)",
                    (user_actual, semana_str, d["fecha"], d["tipo"], desc,
                     d["duracion_min"], d["intensidad"], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            conn.commit(); st.cache_data.clear(); st.success("Plan guardado.")
        except Exception as e:
            st.error(f"Error: {e}")
        finally:
            conn.close()


# ============================================================================
# TAB 2: DATOS DEL ENTRENADOR
# ============================================================================
elif active_tab == "datos":

    # Header with gradient
    st.markdown("""
<div style="background:linear-gradient(135deg,rgba(34,211,238,0.15),rgba(74,222,128,0.1));
border:1px solid rgba(74,222,128,0.25);border-radius:16px;padding:1.5rem 2rem;margin-bottom:1.5rem;">
  <h2 style="color:white;font-size:1.25rem;font-weight:800;margin:0 0 .3rem;">Análisis del Entrenador</h2>
  <p style="color:#8B949E;font-size:.82rem;margin:0;">Datos biométricos y análisis que generan tu plan personalizado</p>
</div>""", unsafe_allow_html=True)

    # Imports específicos de esta sección
    from src.plan.helpers import cargar_datos_plan
    from src.plan.reglas import (
        obtener_fase_macrociclo_usuario, calcular_semaforo,
        aplicar_restricciones_lesion, evaluar_cadencia,
        calcular_volumen_semana, evaluar_eficiencia_aerobica,
    )
    from src.plan.motor import generar_plan_semana
    from src.plan.memoria_fuerza import generar_tabla_fuerza_semana

    _conn_dat = get_db_connection()
    _perfil   = _obtener_perfil(user_actual) or {}
    _genero   = str(_perfil.get("genero", "")).strip().lower()
    _es_mujer = _genero in ("mujer", "female", "f", "w", "femenino")
    _obj_tipo = str(_perfil.get("objetivo_tipo", "")).strip().lower()

    datos = {}
    try:
        datos = cargar_datos_plan(user_actual)
    except Exception as e:
        st.warning(f"No se pudieron cargar datos biométricos: {e}")

    # ── 1. Biométricos ──────────────────────────────────────────────────────
    _section("📊", "Biométricos Actuales", "#00D4FF")

    _m1, _m2, _m3, _m4 = st.columns(4, gap="small")
    _metric_card(_m1, "HRV", f"{datos.get('hrv_actual',0):.0f} ms" if datos.get('hrv_actual') else "—",
                 color="#00D4FF")
    _metric_card(_m2, "Sleep Score", f"{datos.get('sleep_score',0)}/100" if datos.get('sleep_score') else "—",
                 color="#7EB8E0")
    _metric_card(_m3, "Estrés Medio",
                 f"{datos.get('estres_medio',0)}/100" if datos.get('estres_medio') else "—",
                 color="#f97316")
    _metric_card(_m4, "Body Battery",
                 f"{datos.get('body_battery_min',0)}/100" if datos.get('body_battery_min') else "—",
                 color="#a855f7")

    sb = datos.get("sleep_breakdown", {})
    if sb:
        _s1, _s2, _s3, _s4 = st.columns(4, gap="small")
        _metric_card(_s1, "Sueño Total",   f"{sb.get('horas_totales','—'):.1f}h" if sb.get('horas_totales') is not None else "—", color="#7EB8E0")
        _metric_card(_s2, "Profundo",      f"{sb.get('profundo_h','—'):.1f}h"    if sb.get('profundo_h')    is not None else "—", color="#22c55e")
        _metric_card(_s3, "REM",           f"{sb.get('rem_h','—'):.1f}h"         if sb.get('rem_h')         is not None else "—", color="#f59e0b")
        _metric_card(_s4, "Vigilia",       f"{sb.get('vigilia_h','—'):.1f}h"     if sb.get('vigilia_h')     is not None else "—", color="#ef4444")

    # ── 2. Tablas de Sueño y Biométricos ────────────────────────────────────
    _section("😴", "Sueño — Últimos 30 Días", "#7EB8E0")

    try:
        _df_sueno = pd.read_sql_query(
            """SELECT fecha,
                      ROUND(horas_totales, 1) as horas_totales,
                      score,
                      ROUND(sleep_profundo_horas, 1) as deep_sleep_h,
                      ROUND(sleep_rem_horas, 1) as rem_sleep_h,
                      ROUND(sleep_vigilia_horas, 1) as awake_h
               FROM datos_sueno
               WHERE usuario_id=? AND fecha >= date('now','-30 days')
               ORDER BY fecha DESC""",
            _conn_dat, params=(user_actual,))

        if not _df_sueno.empty:
            # Rename columns for display
            _df_sueno_display = _df_sueno.copy()
            _df_sueno_display.columns = ["Fecha", "Total (h)", "Score", "Profundo (h)", "REM (h)", "Vigilia (h)"]
            st.dataframe(_df_sueno_display, use_container_width=True, hide_index=True)
        else:
            st.info("Sin datos de sueño en los últimos 30 días. Sincroniza tu dispositivo Garmin.")
    except Exception as e:
        st.caption(f"Error cargando datos de sueño: {e}")

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    # ── 2b. Biométricos Diarios ─────────────────────────────────────────────
    _section("❤️", "Biométricos — Últimos 30 Días", "#3B82F6")

    try:
        _df_biom = pd.read_sql_query(
            """SELECT fecha,
                      ROUND(hrv_ms) as hrv_ms,
                      fc_reposo as rhr,
                      sleep_score,
                      ROUND(estres_medio) as stress_level_avg,
                      body_battery_min
               FROM datos_biometricos_premium
               WHERE usuario_id=? AND fecha >= date('now','-30 days')
               ORDER BY fecha DESC""",
            _conn_dat, params=(user_actual,))

        if not _df_biom.empty:
            # Rename columns for display
            _df_biom_display = _df_biom.copy()
            _df_biom_display.columns = ["Fecha", "HRV (ms)", "RHR", "Sleep Score", "Estrés", "Battery"]
            st.dataframe(_df_biom_display, use_container_width=True, hide_index=True)
        else:
            st.info("Sin datos biométricos en los últimos 30 días. Sincroniza tu dispositivo Garmin.")
    except Exception as e:
        st.caption(f"Error cargando datos biométricos: {e}")

    st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)

    # ── 3. Análisis de Carrera ──────────────────────────────────────────────
    _section("🏃", "Análisis de Carrera & Rendimiento", "#22c55e")

    _r1, _r2, _r3 = st.columns(3, gap="small")
    _cad_raw = datos.get("cadencia_media", 0)
    _cad = _cad_raw if isinstance(_cad_raw, (int, float)) and _cad_raw is not None else 0
    _cad_note = "↓ Mejorar técnica" if _cad < 170 else ("↑ Excelente" if _cad > 175 else "→ Normal")
    _acwr_raw = datos.get("acwr", 0)
    _acwr_v = _acwr_raw if isinstance(_acwr_raw, (int, float)) and _acwr_raw is not None else 0
    _acwr_note = "🔴 Elevado" if _acwr_v > 1.5 else ("🟡 Moderado" if _acwr_v > 1.3 else "🟢 Normal")
    _metric_card(_r1, "Cadencia Media", f"{_cad:.0f} spm", _cad_note, color="#22c55e")
    _metric_card(_r2, "VO2max",         "—",               "No disponible", color="#8B949E")
    _metric_card(_r3, "ACWR",           f"{_acwr_v:.2f}",  _acwr_note, color="#f59e0b" if _acwr_v > 1.3 else "#22c55e")

    try:
        df_act_week = pd.read_sql_query(
            """SELECT fecha, ROUND(distancia_m/1000,2) as km, cadencia_media, fc_media, ritmo_medio
               FROM actividades_garmin
               WHERE usuario_id=? AND fecha >= date('now','-7 days')
               AND LOWER(COALESCE(tipo_deporte,'')) LIKE '%run%'
               ORDER BY fecha DESC""",
            _conn_dat, params=(user_actual,))
        if not df_act_week.empty:
            st.markdown("<div style='margin-top:0.5rem;'></div>", unsafe_allow_html=True)
            st.caption("Últimas actividades de running (7 días)")
            st.dataframe(df_act_week, use_container_width=True, hide_index=True)
        else:
            st.caption("Sin actividades de running en los últimos 7 días.")
    except Exception:
        pass

    # ── 4. Fase del Macrociclo ──────────────────────────────────────────────
    _section("📅", "Fase del Macrociclo", "#C9FF00")

    _fase_dat = obtener_fase_macrociclo_usuario(user_actual)
    _fecha_obj_s = _perfil.get("fecha_objetivo")
    _dias_rest = _sem_rest = None
    if _fecha_obj_s:
        try:
            _fobj = datetime.strptime(str(_fecha_obj_s), "%Y-%m-%d")
            _dias_rest = (_fobj - datetime.now()).days
            _sem_rest  = _dias_rest // 7
        except Exception:
            pass

    _f1, _f2, _f3 = st.columns(3, gap="small")
    _metric_card(_f1, "Fase Actual",    _fase_dat.get("fase_nombre","—"),          color="#C9FF00")
    _metric_card(_f2, "KM Máx/Semana", f"{_fase_dat.get('km_semanales_max',0)} km", color="#00D4FF")
    _metric_card(_f3, "Días Fuerza",   f"{_fase_dat.get('dias_fuerza',0)} días",    color="#a855f7")

    if _dias_rest is not None:
        _d1, _d2 = st.columns(2, gap="small")
        _metric_card(_d1, "Días hasta objetivo", str(_dias_rest), color="#f59e0b")
        _metric_card(_d2, "Semanas hasta objetivo", str(_sem_rest), color="#f59e0b")

    st.markdown(
        f"<div style='background:#0f1724;border:1px solid rgba(201,255,0,0.1);border-radius:10px;"
        f"padding:0.75rem 1rem;margin-top:0.5rem;font-size:0.8rem;color:#9ca3af;'>"
        f"<b style='color:#C9E1FF;'>Enfoque Running:</b> {_fase_dat.get('enfoque_running','—')}<br>"
        f"<b style='color:#C9E1FF;'>Enfoque Fuerza:</b> {_fase_dat.get('enfoque_fuerza','—')}</div>",
        unsafe_allow_html=True)

    # ── 5. Semáforo ─────────────────────────────────────────────────────────
    _section("🚦", "Semáforo de Recuperación", "#f59e0b")

    _sem_dat = calcular_semaforo(
        hrv_actual=datos.get("hrv_actual"),
        hrv_media_7d=datos.get("hrv_media_7d"),
        sleep_score=datos.get("sleep_score"),
        sleep_breakdown=datos.get("sleep_breakdown"),
        estres_medio=datos.get("estres_medio"),
        body_battery_min=datos.get("body_battery_min"),
        training_status=datos.get("training_status"),
    )
    _color_map = {"verde": "#22c55e", "ambar": "#f59e0b", "rojo": "#ef4444"}
    _sc = _color_map.get(_sem_dat["color"], "#9ca3af")
    _icono = {"verde":"🟢","ambar":"💡","rojo":"💡"}.get(_sem_dat["color"],"💡")
    _titulo = "Recuperación óptima" if _sem_dat["color"] == "verde" else "Recomendación de recuperación"
    st.info(
        f"{_icono} {_titulo}\n\n"
        f"{_sem_dat['mensaje']}\n"
        "El plan se genera con carga completa. Aplica estas recomendaciones si lo consideras necesario.\n"
        f"Multiplicador volumen: {_sem_dat['multiplicador_volumen']:.2f}x · "
        f"Calidad permitida: {'Sí' if _sem_dat['permitir_calidad'] else 'No'}"
    )

    # ── 6. Ciclo (mujeres) ──────────────────────────────────────────────────
    ciclo_data = None
    if _es_mujer:
        _section("🩸", "Ciclo Menstrual", "#ec4899")
        ciclo_data = datos.get("ciclo_menstrual") or datos.get("fase_ciclo")
        if ciclo_data:
            _c1, _c2, _c3 = st.columns(3, gap="small")
            _metric_card(_c1, "Fase", ciclo_data.get("fase") or ciclo_data.get("fase_nombre","—"), color="#ec4899")
            _metric_card(_c2, "Multiplicador Vol.", f"{ciclo_data.get('multiplicador_volumen',1):.2f}x", color="#ec4899")
            _metric_card(_c3, "¿Calidad permitida?", "Sí" if ciclo_data.get("permitir_calidad",True) else "No", color="#ec4899")
            st.info("💡 El ciclo menstrual se usa como recomendación. El plan semanal se mantiene completo y tú decides si ajustar intensidad.")
            if ciclo_data.get("hidratacion_extra"):
                st.info("💧 Fase de estrés hormonal — aumentar hidratación y electrolitos.")
        else:
            st.info("Sin datos de ciclo. Añade registros en la pestaña Diario.")

    # ── 7. Restricciones / Lesiones ─────────────────────────────────────────
    _section("⚠️", "Restricciones & Lesiones Activas", "#ef4444")

    _restricciones = aplicar_restricciones_lesion(datos.get("lesiones_activas", []))
    if datos.get("lesiones_activas"):
        st.error(f"**{len(datos['lesiones_activas'])} lesión(es) activa(s)**")
        for _les in datos["lesiones_activas"]:
            st.markdown(
                f"- **{_les.get('tipo','?')}** (Grado {_les.get('grado','?')}/10) — "
                f"{', '.join(_restricciones.get('alertas',[]) or ['Sin restricciones específicas'])}")
    else:
        st.success("✅ Sin lesiones activas")

    # ── 8. Evaluaciones Especializadas ──────────────────────────────────────
    _section("🔍", "Evaluaciones Especializadas", "#6366f1")

    _e1, _e2, _e3 = st.columns(3, gap="small")
    _cad_eval = evaluar_cadencia(datos.get("cadencia_media"))
    with _e1:
        st.markdown(f"<div style='font-size:0.72rem;font-weight:700;color:#8B949E;text-transform:uppercase;"
                    f"letter-spacing:.07em;margin-bottom:6px;'>Cadencia</div>", unsafe_allow_html=True)
        (st.warning if _cad_eval.get("necesita_drills") else st.success)(f"{'🔧' if _cad_eval.get('necesita_drills') else '✅'} {_cad_eval.get('mensaje','—')}")

    _efic = evaluar_eficiencia_aerobica(datos.get("actividades_z2", []))
    with _e2:
        st.markdown(f"<div style='font-size:0.72rem;font-weight:700;color:#8B949E;text-transform:uppercase;"
                    f"letter-spacing:.07em;margin-bottom:6px;'>Eficiencia Aeróbica</div>", unsafe_allow_html=True)
        if _efic.get("tendencia") == "sin_datos":
            st.info("Sin datos suficientes (mín. 4 sesiones Z2 en 28 días).")
        elif _efic.get("necesita_fartlek"):
            st.warning("⚠️ Tendencia estancada. Añadir fartlek suave.")
        else:
            st.success("✅ Tendencia positiva")

    _km_obj = calcular_volumen_semana(
        datos.get("km_semana_anterior", 15), datos.get("acwr", 0.8),
        datos.get("lesiones_activas", []), _fase_dat.get("km_semanales_max", 60))
    with _e3:
        _metric_card(_e3, "Volumen Estimado Semana", f"{_km_obj:.1f} km", color="#C9FF00")

    # ── 9. Tabla de Fuerza ──────────────────────────────────────────────────
    _section("💪", "Sesión de Fuerza Propuesta", "#a855f7")

    try:
        _tabla_f = generar_tabla_fuerza_semana(user_actual, _fase_dat, _sem_dat,
                                               acwr=datos.get("acwr"), conn=_conn_dat)
        _df_f = pd.DataFrame(_tabla_f)
        if "Día" in _df_f.columns:
            for _dia in ["Push", "Pull", "Tren inferior + glúteo"]:
                _df_dia = _df_f[_df_f["Día"] == _dia]
                if not _df_dia.empty:
                    st.markdown(f"**{_dia}**")
                    st.dataframe(_df_dia.drop(columns=["Día"]), use_container_width=True, hide_index=True)
        else:
            st.dataframe(_df_f, use_container_width=True, hide_index=True)
    except Exception as e:
        st.caption(f"No se pudo generar tabla de fuerza: {e}")

    # ── 10. Resumen Ejecutivo ───────────────────────────────────────────────
    _section("📌", "Resumen Ejecutivo", "#00D4FF")

    _rx1, _rx2 = st.columns(2, gap="small")
    with _rx1:
        _km_tot_dat = float(st.session_state.plan_data.get("km_totales", 0)) if st.session_state.plan_data else 0
        st.markdown(f"""
<div style="background:#0f1724;border:1px solid rgba(0,212,255,0.15);border-radius:12px;padding:1rem;">
  <div style="color:#8B949E;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">Estado de Entrenamiento</div>
  <div style="font-size:0.8rem;color:#C9E1FF;line-height:2;">
    Recuperación: <b style="color:{_sc};">{_sem_dat['color'].upper()}</b><br>
    Volumen objetivo: <b style="color:#C9FF00;">{_km_tot_dat:.1f} km</b><br>
    Calidad permitida: <b>{'Sí' if _sem_dat['permitir_calidad'] else 'No — Solo Z1/Z2'}</b><br>
    ACWR: <b>{datos.get('acwr',0):.2f}</b>
  </div>
</div>""", unsafe_allow_html=True)
    with _rx2:
        st.markdown(f"""
<div style="background:#0f1724;border:1px solid rgba(0,212,255,0.15);border-radius:12px;padding:1rem;">
  <div style="color:#8B949E;font-size:0.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;margin-bottom:8px;">Ajustes Aplicados</div>
  <div style="font-size:0.8rem;color:#C9E1FF;line-height:2;">
    Ciclo menstrual: <b>{ciclo_data.get('fase','N/A') if (_es_mujer and ciclo_data) else ('N/A' if _es_mujer else 'No aplica')}</b><br>
    Drills cadencia: <b>{'Sí — 5min técnica' if _cad_eval.get('necesita_drills') else 'No necesarios'}</b><br>
    Lesiones: <b>{'Sí — sustituciones aplicadas' if datos.get('lesiones_activas') else 'Ninguna'}</b><br>
    Fase: <b>{_fase_dat.get('fase_nombre','—')}</b>
  </div>
</div>""", unsafe_allow_html=True)

    st.success("✅ Datos listos para generar tu plan semanal personalizado.")

    if _conn_dat:
        try:
            _conn_dat.close()
        except Exception:
            pass
"""
src/core/plan_ui_helpers.py
Helpers HTML para la UI del plan semanal (pages/2_plan.py).
"""

from datetime import datetime

_INICIO_MACRO = datetime(2026, 3, 1)
_FIN_MACRO    = datetime(2027, 2, 21)

_BG_SEM   = {"verde": "#0d3b2e", "ambar": "#3b2e00", "rojo": "#3b0d0d"}
_BORD_SEM = {"verde": "#00C896", "ambar": "#F5A623", "rojo": "#FF4444"}
_ICON_SEM = {"verde": "🟢",      "ambar": "🟡",      "rojo": "🔴"}

_BADGE_COLOR = {
    "Fuerza": "#9B59B6", "Fuerza Activ.": "#9B59B6", "Fuerza Tren Superior": "#9B59B6",
    "Fuerza Push": "#9B59B6", "Fuerza Pull": "#9B59B6", "Fuerza Pierna": "#9B59B6",
    "Tirada Larga": "#C9FF00", "Progresiva": "#C9FF00", "Carrera Z2": "#C9FF00",
    "Tempo (umbral)": "#C9FF00", "Intervalos VO2max": "#FF6B6B", "Calidad": "#FF6B6B",
    "Regenerativo": "#00C8C8", "Rodaje Corto": "#7EB8E0",
    "Descanso": "#3a4150", "Movilidad": "#3a4150", "Sustitución": "#F5A623",
}

_EMOJIS = {
    "Tirada Larga": "🏃", "Progresiva": "📈", "Tempo (umbral)": "⚡",
    "Intervalos VO2max": "🔥", "Carrera Z2": "🚶", "Rodaje Corto": "🏃",
    "Regenerativo": "💧", "Fuerza": "💪", "Fuerza Activ.": "💪",
    "Fuerza Tren Superior": "💪", "Fuerza Push": "💪", "Fuerza Pull": "💪",
    "Fuerza Pierna": "💪", "Descanso": "🛌", "Movilidad": "🧘",
    "Sustitución": "🔄",
}

_ZONA_COLOR = {"Z1": "#00C896", "Z2": "#C9FF00", "Z3": "#F5A623", "Z4": "#FF6B6B", "Z5": "#FF0044"}


def html_semaforo(semaforo: dict, km_totales: float, acwr: float) -> str:
    c = semaforo["color"]
    titulo = "💡 Recomendación de recuperación" if c in ("rojo", "ambar") else f"Semáforo {c.upper()}"
    return (
        f"<div style='background:{_BG_SEM[c]};border:2px solid {_BORD_SEM[c]};"
        f"border-radius:14px;padding:14px 20px;margin-bottom:16px;"
        f"display:flex;align-items:center;gap:14px;'>"
        f"<span style='font-size:2rem;'>{_ICON_SEM[c]}</span>"
        f"<div><div style='font-size:1.05rem;font-weight:800;color:{_BORD_SEM[c]};'>"
        f"{titulo}</div>"
        f"<div style='color:#d8e9db;font-size:0.85rem;margin-top:2px;'>{semaforo['mensaje']}</div>"
        f"<div style='color:#8B949E;font-size:0.75rem;margin-top:2px;'>"
        f"ACWR: {acwr} · Objetivo: {km_totales} km</div></div></div>"
    )


def html_barra_fase(fase: dict) -> str:
    dias = max(1, (_FIN_MACRO - _INICIO_MACRO).days)
    pct = min(100, max(0, int(100 * (datetime.now() - _INICIO_MACRO).days / dias)))
    return (
        f"<div style='background:#131D2B;border:1px solid rgba(201,255,0,0.3);"
        f"border-radius:12px;padding:10px 16px;margin-bottom:16px;'>"
        f"<div style='display:flex;justify-content:space-between;'>"
        f"<span style='font-weight:800;color:#C9FF00;'>{fase['fase_nombre']}</span>"
        f"<span style='color:#8B949E;font-size:0.78rem;'>{pct}% completado</span></div>"
        f"<div style='background:#0c2922;border-radius:4px;height:6px;margin:6px 0;'>"
        f"<div style='background:#C9FF00;width:{pct}%;height:6px;border-radius:4px;'></div></div>"
        f"<div style='color:#d8e9db;font-size:0.78rem;'>{fase['enfoque_running']}</div>"
        f"<div style='color:#8B949E;font-size:0.72rem;margin-top:2px;'>{fase['enfoque_fuerza']}</div>"
        f"</div>"
    )


def html_fila_dia(dia: dict, seleccionado: bool) -> str:
    color = _BADGE_COLOR.get(dia["tipo"], "#8B949E")
    emoji = _EMOJIS.get(dia["tipo"], "📅")
    km_txt = f"{dia['km']} km" if dia["km"] else f"{dia['duracion_min']}'"
    borde = "2px solid #C9FF00" if seleccionado else "1px solid rgba(201,255,0,0.15)"
    bg = "#1a2e3b" if seleccionado else "#131D2B"
    return (
        f"<div style='background:{bg};border:{borde};border-radius:10px;"
        f"padding:8px 12px;margin-bottom:6px;cursor:pointer;'>"
        f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
        f"<div>"
        f"<span style='font-weight:700;color:#C9E1FF;font-size:0.85rem;'>{dia['dia']}</span>"
        f"<span style='color:#8B949E;font-size:0.7rem;margin-left:6px;'>{dia['fecha'][5:]}</span>"
        f"</div>"
        f"<span style='background:{color}22;color:{color};border:1px solid {color}66;"
        f"border-radius:6px;padding:1px 7px;font-size:0.72rem;font-weight:700;'>{emoji} {dia['tipo']}</span>"
        f"</div>"
        f"<div style='color:#8B949E;font-size:0.75rem;margin-top:2px;'>{km_txt} · {dia['intensidad']}</div>"
        f"</div>"
    )


def html_detalle_carrera(dia: dict, bloques: list) -> str:
    km_txt = f"{dia['km']} km" if dia["km"] else "—"
    dur_txt = f"{dia['duracion_min']} min"
    stats = (
        f"<div style='display:flex;gap:12px;margin:10px 0;flex-wrap:wrap;'>"
        f"<div style='background:#0c2922;border-radius:8px;padding:8px 14px;'>"
        f"<div style='color:#8B949E;font-size:0.7rem;'>DISTANCIA</div>"
        f"<div style='color:#C9FF00;font-weight:800;font-size:1rem;'>{km_txt}</div></div>"
        f"<div style='background:#0c2922;border-radius:8px;padding:8px 14px;'>"
        f"<div style='color:#8B949E;font-size:0.7rem;'>DURACIÓN</div>"
        f"<div style='color:#C9FF00;font-weight:800;font-size:1rem;'>{dur_txt}</div></div>"
        f"<div style='background:#0c2922;border-radius:8px;padding:8px 14px;'>"
        f"<div style='color:#8B949E;font-size:0.7rem;'>INTENSIDAD</div>"
        f"<div style='color:#C9FF00;font-weight:800;font-size:1rem;'>{dia['intensidad']}</div></div>"
        f"</div>"
    )
    bloques_html = ""
    for b in bloques:
        c = _ZONA_COLOR.get(b["zona"], "#C9FF00")
        bloques_html += (
            f"<div style='display:flex;align-items:center;gap:10px;padding:6px 10px;"
            f"background:#0c2922;border-radius:6px;margin-bottom:4px;'>"
            f"<div style='width:10px;height:10px;border-radius:50%;background:{c};flex-shrink:0;'></div>"
            f"<span style='color:#d8e9db;font-size:0.83rem;font-weight:700;min-width:30px;'>{b['zona']}</span>"
            f"<span style='color:#8B949E;font-size:0.8rem;'>{b['duracion_min']:.0f} min</span>"
            f"<span style='color:{c};font-size:0.72rem;margin-left:auto;'>{b['tipo']}</span>"
            f"</div>"
        )
    alerta = (f"<div style='background:#3b2e00;border:1px solid #F5A623;border-radius:8px;"
              f"padding:8px;margin-top:8px;color:#F5A623;font-size:0.8rem;'>⚠️ {dia['alerta']}</div>"
              if dia.get("alerta") else "")
    return stats + "<div style='margin:8px 0 4px;color:#8B949E;font-size:0.75rem;font-weight:700;'>BLOQUES</div>" + bloques_html + alerta


def html_detalle_fuerza(dia: dict) -> str:
    return (
        f"<div style='background:#1a0b2e;border:1px solid #9B59B666;border-radius:12px;"
        f"padding:14px;margin-bottom:8px;'>"
        f"<div style='font-weight:800;color:#9B59B6;font-size:1rem;margin-bottom:4px;'>💪 {dia['tipo']}</div>"
        f"<div style='color:#d8e9db;font-size:0.85rem;'>{dia['duracion_min']} min · {dia['intensidad']}</div>"
        f"<div style='color:#8B949E;font-size:0.78rem;margin-top:6px;'>"
        f"Ver tabla de ejercicios y pesos sugeridos abajo.</div></div>"
    )


def html_detalle_descanso(dia: dict) -> str:
    return (
        f"<div style='background:#131D2B;border:1px dashed #3a4150;border-radius:12px;"
        f"padding:20px;text-align:center;'>"
        f"<div style='font-size:2rem;'>🛌</div>"
        f"<div style='color:#8B949E;font-size:0.9rem;margin-top:8px;'>Descanso activo · Movilidad opcional</div>"
        f"</div>"
    )

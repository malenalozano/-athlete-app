"""
src/core/zonas_ritmo.py
Calcula ritmos medios por zona FC (Z1-Z5) a partir de actividades_garmin.

Las zonas se calculan en función de FCmax (220-edad si no hay dato real,
o el máximo histórico de fc_max en actividades).

Uso:
    rit = ritmos_por_zona(usuario_id)
    # rit = {"Z1": 7.8, "Z2": 6.9, "Z3": 6.0, "Z4": 5.4, "Z5": 4.8}  (min/km)

    pace = ritmo_para_intensidad(rit, "Z2")           -> 6.9
    km, dur = estimar_km_duracion(60, "Z2", rit)      -> (8.7, 60.0) p.ej.
"""
from __future__ import annotations

import pandas as pd

from src.db.db_manager import get_db_connection, obtener_perfil

# Umbrales de %FCmax por zona (Karvonen simplificado / Coggan)
_ZONAS_PCT = {
    "Z1": (0.50, 0.60),
    "Z2": (0.60, 0.70),
    "Z3": (0.70, 0.80),
    "Z4": (0.80, 0.90),
    "Z5": (0.90, 1.05),
}

# Ritmos por defecto (si no hay datos del usuario aún) — corredor amateur
_DEFAULT_RITMOS = {"Z1": 8.0, "Z2": 7.0, "Z3": 6.2, "Z4": 5.5, "Z5": 4.8}


def _fc_max_usuario(usuario_id: int) -> int:
    """FCmax estimada: máximo histórico fc_max en actividades, o 220-edad."""
    conn = get_db_connection()
    try:
        row = conn.execute(
            "SELECT MAX(fc_max) FROM actividades_garmin WHERE usuario_id=?",
            (usuario_id,),
        ).fetchone()
        if row and row[0]:
            return int(row[0])
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    perfil = obtener_perfil(usuario_id) or {}
    edad = int(perfil.get("edad") or 30)
    return max(150, 220 - edad)


def ritmos_por_zona(usuario_id: int, dias: int = 90) -> dict:
    """
    Devuelve {Z1: ritmo_min_km, ..., Z5: ritmo_min_km} promediando sesiones
    cuya FC media cae en el rango de cada zona durante los últimos `dias`.
    Si no hay datos en una zona, rellena con valores por defecto.
    """
    fc_max = _fc_max_usuario(usuario_id)
    rangos = {
        z: (round(fc_max * a), round(fc_max * b))
        for z, (a, b) in _ZONAS_PCT.items()
    }

    conn = get_db_connection()
    try:
        df = pd.read_sql_query(
            """SELECT distancia_m, tiempo_seg, ritmo_medio, fc_media
               FROM actividades_garmin
               WHERE usuario_id=?
                 AND fecha >= date('now', '-' || ? || ' days')
                 AND tipo_deporte LIKE '%running%'
                 AND fc_media IS NOT NULL
                 AND distancia_m > 0""",
            conn, params=(usuario_id, int(dias)))
    except Exception:
        df = pd.DataFrame()
    finally:
        try:
            conn.close()
        except Exception:
            pass

    out = dict(_DEFAULT_RITMOS)
    if df.empty:
        return out

    df["distancia_km"] = pd.to_numeric(df["distancia_m"], errors="coerce") / 1000.0
    df["tiempo_seg"] = pd.to_numeric(df["tiempo_seg"], errors="coerce")
    df["ritmo_medio"] = pd.to_numeric(df["ritmo_medio"], errors="coerce")
    df["fc_media"] = pd.to_numeric(df["fc_media"], errors="coerce")

    # Ritmo en min/km: prefer ritmo_medio si existe, si no calcula
    pace = df["ritmo_medio"].copy()
    falta = pace.isna() | (pace <= 0)
    pace.loc[falta] = (df.loc[falta, "tiempo_seg"] / 60.0) / df.loc[falta, "distancia_km"]
    df["pace_min_km"] = pace
    df = df[df["pace_min_km"].notna() & (df["pace_min_km"] > 2) & (df["pace_min_km"] < 15)]
    if df.empty:
        return out

    for z, (lo, hi) in rangos.items():
        sub = df[(df["fc_media"] >= lo) & (df["fc_media"] < hi)]
        if not sub.empty:
            out[z] = round(float(sub["pace_min_km"].mean()), 2)
    return out


# ── Mapeo tipo de entrenamiento → zona dominante ─────────────────────────
_TIPO_A_ZONA = {
    "Tirada Larga": "Z2",
    "Carrera Z2": "Z2",
    "Rodaje Corto": "Z2",
    "Regenerativo": "Z1",
    "Tempo (umbral)": "Z4",
    "Tempo": "Z4",
    "Progresiva": "Z3",
    "Progresivas": "Z3",
    "Cambios de Ritmo": "Z4",
    "Cambios de ritmo": "Z4",
    "Fartlek": "Z4",
    "Intervalos": "Z5",
    "Intervalos VO2max": "Z5",
    "Calidad": "Z4",
    "Libre": "Z2",
}


def zona_de_tipo(tipo: str) -> str:
    """Devuelve la zona FC dominante para un tipo de carrera."""
    t = str(tipo or "").strip()
    if t in _TIPO_A_ZONA:
        return _TIPO_A_ZONA[t]
    tl = t.lower()
    if "regen" in tl:
        return "Z1"
    if "z2" in tl or "tirada" in tl or "rodaje" in tl:
        return "Z2"
    if "progres" in tl:
        return "Z3"
    if "tempo" in tl or "umbral" in tl or "cambios" in tl or "fartlek" in tl:
        return "Z4"
    if "interval" in tl or "vo2" in tl or "calidad" in tl:
        return "Z5"
    return "Z2"


def ritmo_para_tipo(tipo: str, ritmos: dict | None = None,
                    usuario_id: int | None = None) -> float:
    """min/km esperados para un tipo de sesión."""
    if ritmos is None and usuario_id is not None:
        ritmos = ritmos_por_zona(usuario_id)
    if not ritmos:
        ritmos = dict(_DEFAULT_RITMOS)
    return float(ritmos.get(zona_de_tipo(tipo), ritmos.get("Z2", 7.0)))


def estimar_km_desde_min(duracion_min: float, tipo: str,
                         ritmos: dict | None = None,
                         usuario_id: int | None = None) -> float:
    """km estimados para una sesión de duracion_min en zona del tipo."""
    pace = ritmo_para_tipo(tipo, ritmos, usuario_id)
    if pace <= 0 or duracion_min <= 0:
        return 0.0
    return round(float(duracion_min) / pace, 1)


def estimar_min_desde_km(km: float, tipo: str,
                         ritmos: dict | None = None,
                         usuario_id: int | None = None) -> float:
    """min estimados para correr `km` a la zona del tipo."""
    pace = ritmo_para_tipo(tipo, ritmos, usuario_id)
    if pace <= 0 or km <= 0:
        return 0.0
    return round(float(km) * pace, 0)


def calidad_sesion(km_real: float, dur_real: float, fc_real: float | None,
                   tipo_plan: str, km_plan: float, dur_plan: float,
                   ritmos: dict, fc_max: int = 0) -> str:
    """
    Clasifica una sesión realizada como 'bueno' | 'normal' | 'malo'.

    Reglas:
      - malo: km muy por debajo (<60%) o ritmo mucho peor (>+15%) o FC fuera de zona
      - bueno: ritmo mejor que la media de zona, o más km a menos tiempo
      - normal: dentro del rango esperado
    """
    if km_real <= 0 or dur_real <= 0:
        return "normal"
    pace_real = dur_real / km_real if km_real > 0 else 0
    pace_zona = ritmo_para_tipo(tipo_plan, ritmos)
    zona = zona_de_tipo(tipo_plan)

    # Ratio km vs plan
    ratio_km = (km_real / km_plan) if km_plan > 0 else 1.0
    # Ritmo: positivo = más rápido que la media de la zona
    delta_pace = (pace_zona - pace_real) / pace_zona if pace_zona > 0 else 0

    # FC fuera de zona programada (margen ±5 ppm)
    fc_fuera = False
    if fc_real and fc_max > 0:
        rngs = _ZONAS_PCT.get(zona)
        if rngs:
            lo = fc_max * rngs[0] - 5
            hi = fc_max * rngs[1] + 5
            if fc_real < lo or fc_real > hi:
                fc_fuera = True

    # MALO
    if ratio_km < 0.6 and km_plan > 0:
        return "malo"
    if delta_pace < -0.15:  # >15% más lento
        return "malo"
    if fc_fuera and zona in ("Z1", "Z2"):  # zonas suaves: si te pasaste mucho de FC, malo
        return "malo"

    # BUENO
    if delta_pace > 0.05 and ratio_km >= 0.95:
        return "bueno"
    if ratio_km >= 1.10 and delta_pace >= 0:
        return "bueno"

    return "normal"

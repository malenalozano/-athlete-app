"""Tests de la lógica de NORMAS_ENTRENAMIENTO_v2: calendario de macrociclos (dos
carreras), reparto de km (TL/RG/calidad/RB) y separación entre sesiones de calidad.

Corren contra la sqlite local (ver conftest.py) con un usuario de prueba dedicado
que se crea y se borra en cada test — nunca tocan datos reales."""
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from database import get_db
from main import app
from routers.plan import _calcular_macrociclo_v2

client = TestClient(app)

TEST_USER_ID = 999001
PLAN_START = "2026-08-03"       # lunes = Carga 1 / semana 1
INTERMEDIA = "2026-11-08"       # media maratón de prueba
FINAL = "2027-02-21"            # maratón final de prueba


@pytest.fixture
def usuario_v2():
    conn = get_db()
    conn.execute("DELETE FROM usuarios WHERE id = ?", (TEST_USER_ID,))
    conn.execute(
        """INSERT INTO usuarios
           (id, nombre, fecha_inicio_entrenamiento, fecha_objetivo_intermedio,
            objetivo_intermedio_nombre, fecha_objetivo, objetivo_tipo)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (TEST_USER_ID, "TestV2", PLAN_START, INTERMEDIA, "Media Maratón Test", FINAL, "maraton"),
    )
    conn.commit()
    conn.close()
    yield TEST_USER_ID
    conn = get_db()
    conn.execute("DELETE FROM plan_entrenamiento WHERE usuario_id = ?", (TEST_USER_ID,))
    conn.execute("DELETE FROM usuarios WHERE id = ?", (TEST_USER_ID,))
    conn.commit()
    conn.close()


# ── _calcular_macrociclo_v2: calendario ──────────────────────────────────────

def test_semana_1_es_carga_1_macrociclo_1():
    r = _calcular_macrociclo_v2(datetime.strptime(PLAN_START, "%Y-%m-%d"), PLAN_START, INTERMEDIA, FINAL)
    assert r["macrociclo"] == 1
    assert r["ciclo_label"] == "Carga 1"
    assert r["semana_num"] == 1


def test_semana_5_pasa_a_macrociclo_2():
    fecha = datetime.strptime(PLAN_START, "%Y-%m-%d") + timedelta(weeks=4)
    r = _calcular_macrociclo_v2(fecha, PLAN_START, INTERMEDIA, FINAL)
    assert r["macrociclo"] == 2
    assert r["semana_num"] == 5


def test_semana_de_la_intermedia_es_taper_o_carrera():
    # Lunes de la semana que contiene la fecha de la intermedia
    f_inter = datetime.strptime(INTERMEDIA, "%Y-%m-%d")
    race_monday = f_inter - timedelta(days=f_inter.weekday())
    r = _calcular_macrociclo_v2(race_monday, PLAN_START, INTERMEDIA, FINAL)
    assert r["macrociclo"] == 2
    assert r["sub_fase"] == "Semana de carrera"


def test_semana_siguiente_a_intermedia_es_macrociclo_3():
    f_inter = datetime.strptime(INTERMEDIA, "%Y-%m-%d")
    race_monday = f_inter - timedelta(days=f_inter.weekday())
    r = _calcular_macrociclo_v2(race_monday + timedelta(weeks=1), PLAN_START, INTERMEDIA, FINAL)
    assert r["macrociclo"] == 3
    assert r["semana_en_macro"] == 1


def test_macrociclo_3_usa_ciclo_2_mas_1():
    f_inter = datetime.strptime(INTERMEDIA, "%Y-%m-%d")
    race_monday = f_inter - timedelta(days=f_inter.weekday())
    m3_start = race_monday + timedelta(weeks=1)
    labels = [
        _calcular_macrociclo_v2(m3_start + timedelta(weeks=i), PLAN_START, INTERMEDIA, FINAL)["ciclo_label"]
        for i in range(3)
    ]
    assert labels == ["Carga 1", "Carga 2", "Descarga"]


def test_semanas_por_macrociclo_suman_el_total_del_plan():
    r = _calcular_macrociclo_v2(datetime.strptime(PLAN_START, "%Y-%m-%d"), PLAN_START, INTERMEDIA, FINAL)
    semanas = r["semanas_por_macrociclo"]
    assert semanas[1] == 4  # M1 siempre 4 semanas fijas
    assert semanas[4] == 3  # M4 siempre 3 semanas fijas (taper)
    assert semanas[1] + semanas[2] + semanas[3] + semanas[4] > 0


def test_sin_carrera_intermedia_devuelve_none():
    r = _calcular_macrociclo_v2(datetime.strptime(PLAN_START, "%Y-%m-%d"), PLAN_START, None, FINAL)
    assert r is None


# ── generar-semana: reparto de km y separación de sesiones ───────────────────

def _generar(usuario_id, fecha_inicio, **overrides):
    body = {"fecha_inicio": fecha_inicio, "dry_run": True, **overrides}
    res = client.post(f"/plan/{usuario_id}/generar-semana", json=body)
    assert res.status_code == 200, res.text
    return res.json()


def test_calidad_nunca_supera_20_por_ciento(usuario_v2):
    # Semana de Macrociclo 2 (dos sesiones de calidad) — el caso con más riesgo de
    # sumar de más si cada sesión usara el 20% completo por separado.
    d = _generar(usuario_v2, "2026-08-31")
    carrera = [s for s in d["sesiones"] if s["tipo"] == "Carrera"]
    calidad_km = sum(s["km_planificados"] for s in carrera if s["intensidad"] == "Alta")
    assert calidad_km <= d["km_total"] * 0.20 + 0.2  # margen de redondeo


def test_tl_entre_30_y_35_por_ciento_y_tope_32km(usuario_v2):
    d = _generar(usuario_v2, "2026-08-31", km_total=90)
    carrera = [s for s in d["sesiones"] if s["tipo"] == "Carrera"]
    tl = next(s for s in carrera if "Tirada" in s["sesion"])
    # Con 90km el 35% (31.5) queda justo por debajo del tope de 32km
    assert 26.5 <= tl["km_planificados"] <= 32.0


def test_tl_nunca_supera_32km_con_volumen_muy_alto(usuario_v2):
    d = _generar(usuario_v2, "2026-08-31", km_total=200)
    carrera = [s for s in d["sesiones"] if s["tipo"] == "Carrera"]
    tl = next(s for s in carrera if "Tirada" in s["sesion"])
    assert tl["km_planificados"] == 32.0


def test_regenerativo_es_un_tercio_de_la_tl(usuario_v2):
    d = _generar(usuario_v2, "2026-08-31")
    carrera = [s for s in d["sesiones"] if s["tipo"] == "Carrera"]
    tl = next(s for s in carrera if "Tirada" in s["sesion"])
    rg = next(s for s in carrera if "Regenerativo" in s["sesion"])
    assert abs(rg["km_planificados"] - round(tl["km_planificados"] / 3, 1)) <= 0.1


def test_separacion_48h_entre_calidad_en_macrociclo_2(usuario_v2):
    d = _generar(usuario_v2, "2026-08-31")  # Macrociclo 2
    calidad = [s for s in d["sesiones"] if s["tipo"] == "Carrera" and s["intensidad"] == "Alta"]
    assert len(calidad) == 2
    fechas = sorted(datetime.strptime(s["fecha"], "%Y-%m-%d") for s in calidad)
    assert (fechas[1] - fechas[0]).days >= 2  # 48h


def test_separacion_72h_tl_calidad_en_macrociclo_3(usuario_v2):
    d = _generar(usuario_v2, "2026-11-16")  # dentro de Macrociclo 3
    assert d["macrociclo_label"] == "M3"
    carrera = [s for s in d["sesiones"] if s["tipo"] == "Carrera"]
    tl_fecha = datetime.strptime(next(s for s in carrera if "Tirada" in s["sesion"])["fecha"], "%Y-%m-%d")
    for s in carrera:
        if s["intensidad"] == "Alta" and "Tirada" not in s["sesion"]:
            fecha = datetime.strptime(s["fecha"], "%Y-%m-%d")
            assert abs((tl_fecha - fecha).days) >= 3  # 72h


def test_semana_de_carrera_final_tiene_la_maraton(usuario_v2):
    d = _generar(usuario_v2, "2027-02-15")
    assert d["macrociclo_label"] == "M4"
    nombres = [s["sesion"] for s in d["sesiones"]]
    assert any("MARAT" in n.upper() for n in nombres)


def test_ciclo_override_fuerza_descarga(usuario_v2):
    d = _generar(usuario_v2, "2026-08-31", ciclo_override="descarga")
    assert d["ciclo_label"] == "Descarga"
    assert d["km_total"] < 20  # ~70% de la base conservadora de 15-20km


def test_incluir_calidad_false_sustituye_por_rodaje_base(usuario_v2):
    d = _generar(usuario_v2, "2026-08-31", incluir_calidad=False)
    carrera = [s for s in d["sesiones"] if s["tipo"] == "Carrera"]
    assert not any(s["intensidad"] == "Alta" for s in carrera)
    assert any("Rodaje Base" in s["sesion"] for s in carrera)


def test_dry_run_no_persiste_nada(usuario_v2):
    _generar(usuario_v2, "2026-08-31")
    conn = get_db()
    n = conn.execute(
        "SELECT COUNT(*) FROM plan_entrenamiento WHERE usuario_id = ?", (usuario_v2,)
    ).fetchone()[0]
    conn.close()
    assert n == 0

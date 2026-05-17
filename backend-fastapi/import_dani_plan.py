"""
Import Dani's training plan from PLAN_Dani.xls into the plan_entrenamiento table.
Run once: python import_dani_plan.py
"""
import xlrd
import re
import sys
import os
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from database import get_db

USUARIO_ID = 2

# Map month name to (year, month)
SHEET_MAP = {
    "Abril 2026":      (2026, 4),
    "Mayo 2026":       (2026, 5),
    "Junio 2026":      (2026, 6),
    "Julio 2026":      (2026, 7),
    "Agosto 2026":     (2026, 8),
    "Septiembre 2026": (2026, 9),
}

# Col index → weekday (0=Mon..6=Sun) for columns Lun/Mar/Mie/Jue/Vie/Sab/Dom
COL_WEEKDAY = {0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 5, 6: 6}


def week_start(d: date) -> str:
    """Return Monday of the week containing d."""
    return (d - timedelta(days=d.weekday())).isoformat()


def parse_km(text: str):
    """Extract km number from strings like '15km', '10km', '27km', '3x1,6km'."""
    # interval: 3x1,6km  → total = 3*1.6 = 4.8 km
    m = re.match(r"(\d+)x([\d,\.]+)km", text, re.I)
    if m:
        reps = int(m.group(1))
        dist = float(m.group(2).replace(",", "."))
        return round(reps * dist, 1)
    # plain km
    m = re.match(r"([\d,\.]+)\s*km", text, re.I)
    if m:
        return float(m.group(1).replace(",", "."))
    return None


def parse_hours(text: str):
    """Extract hours from '3h', '4h', etc. Returns minutes."""
    m = re.match(r"([\d,\.]+)\s*h$", text.strip(), re.I)
    if m:
        return int(float(m.group(1).replace(",", ".")) * 60)
    return None


def classify_activities(lines: list[str]):
    """
    Given list of non-empty lines (after removing the day number line),
    return list of dicts: {tipo, sesion, detalles, km_planificados, duracion_min, intensidad}
    """
    sessions = []

    # Collect gym and running tokens
    gym_tokens = []
    run_tokens = []
    special_tokens = []

    for line in lines:
        l = line.strip()
        if not l:
            continue
        l_lower = l.lower()

        if l_lower in ("descanso",):
            return []  # rest day → no sessions

        if l_lower in ("push", "pull", "legs", "pierna", "core"):
            gym_tokens.append(l.capitalize())
        elif l_lower == "climb":
            run_tokens.append("Climb")
        elif "race day" in l_lower:
            special_tokens.append(l)
        elif "prueba" in l_lower or "esfuerzo" in l_lower:
            special_tokens.append("Prueba de Esfuerzo")
        elif re.match(r"\d+x[\d,\.]+km", l, re.I):
            run_tokens.append(l)
        elif re.match(r"[\d,\.]+\s*km", l, re.I):
            run_tokens.append(l)
        elif re.match(r"[\d,\.]+\s*h$", l, re.I):
            run_tokens.append(l)
        else:
            # unknown → treat as detail note
            special_tokens.append(l)

    # Build running session(s)
    for rt in run_tokens:
        if rt == "Climb":
            sessions.append({
                "tipo": "Carrera",
                "sesion": "Trail / Climb",
                "detalles": "Escalada o trail con desnivel",
                "km_planificados": None,
                "duracion_min": None,
                "intensidad": "Z2",
            })
        elif re.match(r"\d+x[\d,\.]+km", rt, re.I):
            km = parse_km(rt)
            sessions.append({
                "tipo": "Carrera",
                "sesion": f"Intervalos {rt}",
                "detalles": f"Series: {rt}",
                "km_planificados": km,
                "duracion_min": None,
                "intensidad": "Z4",
            })
        elif re.match(r"[\d,\.]+\s*h$", rt, re.I):
            mins = parse_hours(rt)
            sessions.append({
                "tipo": "Carrera",
                "sesion": f"Trail largo {rt}",
                "detalles": f"Salida larga de {rt} en montaña/trail",
                "km_planificados": None,
                "duracion_min": mins,
                "intensidad": "Z2",
            })
        else:
            km = parse_km(rt)
            sessions.append({
                "tipo": "Carrera",
                "sesion": f"Rodaje {rt}" if km else rt,
                "detalles": None,
                "km_planificados": km,
                "duracion_min": None,
                "intensidad": "Z2",
            })

    # Build gym session(s)
    for gt in gym_tokens:
        sessions.append({
            "tipo": "Fuerza",
            "sesion": f"Fuerza — {gt}",
            "detalles": f"Sesión de gimnasio: {gt}",
            "km_planificados": None,
            "duracion_min": 60,
            "intensidad": None,
        })

    # Special sessions (race, test)
    for st in special_tokens:
        sessions.append({
            "tipo": "Carrera",
            "sesion": st,
            "detalles": st,
            "km_planificados": 100 if "100km" in st.lower() else None,
            "duracion_min": None,
            "intensidad": "Carrera",
        })

    return sessions


def parse_cell(cell_val: str, year: int, month: int):
    """Parse a cell value, return (day: int, sessions: list) or None if empty."""
    text = cell_val.strip()
    if not text:
        return None

    lines = [l.strip() for l in text.split("\n")]
    lines = [l for l in lines if l]

    if not lines:
        return None

    # First line is the day number
    try:
        day = int(float(lines[0]))
    except (ValueError, TypeError):
        return None

    activity_lines = lines[1:]
    sessions = classify_activities(activity_lines)
    return day, sessions


def import_plan():
    wb = xlrd.open_workbook("../PLAN_Dani.xls")
    conn = get_db()

    # Clear existing plan for Dani
    deleted = conn.execute("DELETE FROM plan_entrenamiento WHERE usuario_id=?", (USUARIO_ID,)).rowcount
    print(f"Deleted {deleted} existing rows for Dani")

    total_inserted = 0

    for sheet_name, (year, month) in SHEET_MAP.items():
        if sheet_name not in wb.sheet_names():
            continue
        sh = wb.sheet_by_name(sheet_name)

        print(f"\nProcessing {sheet_name}...")

        # Find header row (contains "Lunes")
        header_row = None
        for r in range(sh.nrows):
            row_vals = [str(sh.cell_value(r, c)).strip().lower() for c in range(sh.ncols)]
            if "lunes" in row_vals or "lun" in row_vals:
                header_row = r
                break

        if header_row is None:
            print(f"  No header found, skipping")
            continue

        # Process data rows (after header)
        for r in range(header_row + 1, sh.nrows):
            row = [str(sh.cell_value(r, c)) for c in range(min(sh.ncols, 7))]

            for col_idx, cell_val in enumerate(row):
                result = parse_cell(cell_val, year, month)
                if result is None:
                    continue
                day, sessions = result

                if not sessions:
                    continue

                # Determine the actual date
                # col_idx 0=Mon, 1=Tue, ..., 6=Sun
                # We need to find the date for this day in the spreadsheet
                # The day number is in the cell; we need to figure out which month it belongs to
                # Days 1-28/29/30/31 are in the current month; days that are too small for
                # the expected weekday may belong to the next month
                try:
                    d = date(year, month, day)
                except ValueError:
                    # day out of range for this month - try next month
                    nm = month + 1 if month < 12 else 1
                    ny = year if month < 12 else year + 1
                    try:
                        d = date(ny, nm, day)
                    except ValueError:
                        continue

                # Verify the weekday matches column
                expected_weekday = COL_WEEKDAY[col_idx]
                if d.weekday() != expected_weekday:
                    # Try next month
                    nm = month + 1 if month < 12 else 1
                    ny = year if month < 12 else year + 1
                    try:
                        d2 = date(ny, nm, day)
                        if d2.weekday() == expected_weekday:
                            d = d2
                    except ValueError:
                        pass

                fecha_str = d.isoformat()
                ws = week_start(d)

                for s in sessions:
                    conn.execute(
                        """INSERT INTO plan_entrenamiento
                           (usuario_id, semana_inicio, fecha, tipo, sesion, detalles,
                            duracion_min, intensidad, km_planificados, completado)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
                        (USUARIO_ID, ws, fecha_str, s["tipo"], s["sesion"],
                         s["detalles"], s["duracion_min"], s["intensidad"],
                         s["km_planificados"])
                    )
                    total_inserted += 1
                    print(f"  {fecha_str} ({d.strftime('%a')}): {s['tipo']} — {s['sesion']}")

    conn.commit()
    conn.close()
    print(f"\n✓ Inserted {total_inserted} sessions for Dani (userId={USUARIO_ID})")


if __name__ == "__main__":
    import_plan()

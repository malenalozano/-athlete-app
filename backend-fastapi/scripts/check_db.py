import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
conn = get_db()

print("=== sesiones_fuerza fechas ===")
rows = conn.execute("SELECT fecha, resumen FROM sesiones_fuerza WHERE usuario_id=1 ORDER BY fecha DESC LIMIT 10").fetchall()
for r in rows: print(r)

print("\n=== historial_ejercicio schema ===")
cols = conn.execute("PRAGMA table_info(historial_ejercicio)").fetchall()
for c in cols: print(c)

print("\n=== historial_ejercicio sample ===")
rows2 = conn.execute("SELECT * FROM historial_ejercicio WHERE usuario_id=1 ORDER BY fecha DESC LIMIT 5").fetchall()
for r in rows2: print(r)

print("\n=== ritmo_medio sample (actividades_garmin) ===")
rows3 = conn.execute("SELECT fecha, tipo_deporte, distancia_m, tiempo_seg, ritmo_medio FROM actividades_garmin WHERE usuario_id=1 ORDER BY fecha DESC LIMIT 5").fetchall()
for r in rows3: print(r)

conn.close()

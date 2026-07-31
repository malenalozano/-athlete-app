"""
Lee los tokens Garmin guardados en disco (~/.garth_athlete/)
y los sube directamente a la BD Turso.
Uso: python upload_disk_tokens.py
"""
import sys, os, json, re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db

GARTH_HOME = os.path.expanduser("~/.garth_athlete")

# email -> usuario_id
USUARIOS = {
    "malena.lozanoalonso@gmail.com": 1,
    "orejadaniel5.0@gmail.com": 2,
}

def safe_slug(email):
    return re.sub(r"[^a-z0-9._-]+", "_", email.strip().lower())

conn = get_db()
subidos = 0

for email, uid in USUARIOS.items():
    slug = safe_slug(email)
    token_path = os.path.join(GARTH_HOME, slug, "garmin_tokens.json")
    if not os.path.exists(token_path):
        print(f"  [{uid}] {email}: archivo no encontrado en {token_path}")
        continue
    with open(token_path, "r", encoding="utf-8") as f:
        token_json = f.read()
    conn.execute(
        "UPDATE usuarios SET garmin_tokens = ? WHERE id = ?",
        (token_json, uid),
    )
    print(f"  [{uid}] {email}: tokens subidos (len={len(token_json)})")
    subidos += 1

conn.commit()
conn.close()
print(f"\nListo: {subidos} usuarios actualizados en Turso.")

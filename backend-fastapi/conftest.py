import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Los tests SIEMPRE corren contra la sqlite local, nunca contra Turso (producción).
# Si TURSO_DATABASE_URL/TURSO_AUTH_TOKEN están en el entorno (.env), se ignoran aquí.
os.environ["TURSO_DATABASE_URL"] = ""
os.environ["TURSO_AUTH_TOKEN"] = ""

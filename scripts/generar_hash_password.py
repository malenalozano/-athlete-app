import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.core.access_control import build_password_hash


def main() -> int:
    if len(sys.argv) != 2:
        print("Uso: python scripts/generar_hash_password.py \"tu_password\"")
        return 1

    password = sys.argv[1]
    print(build_password_hash(password))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

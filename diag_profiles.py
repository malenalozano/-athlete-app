import sys
sys.path.insert(0, '.')
from src.db.db_manager import obtener_perfil

# Test both users
for user_id in [1, 2]:
    perfil = obtener_perfil(user_id)
    print(f"\nUser {user_id}:")
    if perfil:
        print(f"  Nombre: {perfil.get('nombre')}")
        print(f"  Objetivo_nombre: {perfil.get('objetivo_nombre')}")
        print(f"  Objetivo_tipo: {perfil.get('objetivo_tipo')}")
        print(f"  Fecha_objetivo: {perfil.get('fecha_objetivo')}")
    else:
        print("  Profile not found!")

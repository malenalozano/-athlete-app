from db_manager import get_db_connection, init_db

conn = get_db_connection()
# Borramos ambas para limpiar bien el esquema
conn.execute("DROP TABLE IF EXISTS entrenamientos_fuerza")
conn.execute("DROP TABLE IF EXISTS datos_sueno")
conn.commit()
conn.close()

# Creamos todo de nuevo
init_db()
print("🚀 ¡Base de Datos reseteada! Tablas de Fuerza y Sueño listas.")   

import sqlite3
import os
from garminconnect import Garmin, GarminConnectConnectionError, GarminConnectAuthenticationError
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Ruta de la base de datos
DB_PATH = os.getenv("DB_PATH", "atleta.db")

def sincronizar_actividades(email, password, usuario_id):
    """
    Sincroniza las últimas 10 actividades de Garmin con la base de datos.
    """
    try:
        # Inicializar cliente Garmin y realizar login
        client = Garmin(email, password)
        client.login()
    except GarminConnectAuthenticationError:
        return "Error: Credenciales de Garmin incorrectas."
    except GarminConnectConnectionError:
        return "Error: No se pudo conectar con Garmin Connect."
    except Exception as e:
        return f"Error inesperado: {e}"

    try:
        # Obtener las últimas 10 actividades
        actividades = client.get_activities(0, 10)
        actividades_sincronizadas = 0

        # Conectar a la base de datos
        conexion = sqlite3.connect(DB_PATH)
        cursor = conexion.cursor()

        for actividad in actividades:
            # Extraer y mapear campos clave
            id_actividad = actividad["activityId"]
            fecha = actividad["startTimeLocal"]
            tipo_deporte = actividad["activityType"]["typeKey"]
            distancia_m = actividad.get("distance", 0)
            tiempo_seg = actividad.get("duration", 0)
            ritmo_medio = 1000 / (actividad.get("averageSpeed", 1) * 60) if actividad.get("averageSpeed") else None
            fc_media = actividad.get("averageHR")
            fc_max = actividad.get("maxHR")

            # Insertar o reemplazar en la base de datos
            cursor.execute('''
                INSERT OR REPLACE INTO actividades_garmin (
                    id_actividad, usuario_id, fecha, tipo_deporte, distancia_m, tiempo_seg, ritmo_medio, fc_media, fc_max
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (id_actividad, usuario_id, fecha, tipo_deporte, distancia_m, tiempo_seg, ritmo_medio, fc_media, fc_max))

            actividades_sincronizadas += 1

        # Guardar cambios y cerrar conexión
        conexion.commit()
        conexion.close()

        return f"Sincronización completada: {actividades_sincronizadas} actividades sincronizadas."
    except sqlite3.Error as e:
        return f"Error de base de datos: {e}"
    except Exception as e:
        return f"Error inesperado durante la sincronización: {e}"

if __name__ == "__main__":
    # Ejemplo de uso
    email = input("Introduce tu correo de Garmin: ")
    password = input("Introduce tu contraseña de Garmin: ")
    usuario_id = int(input("Introduce tu ID de usuario (ej. 1): "))
    resultado = sincronizar_actividades(email, password, usuario_id)
    print(resultado)

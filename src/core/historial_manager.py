def consultar_historial(usuario_id=None, fecha_inicio=None, fecha_fin=None):
    """
    Devuelve una lista de entrenamientos del historial filtrados por usuario y rango de fechas.
    """
    import csv
    from datetime import datetime
    resultados = []
    with open(HISTORIAL_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if usuario_id and row["usuario_id"] != str(usuario_id):
                continue
            if fecha_inicio:
                fecha_row = datetime.strptime(row["fecha"], "%Y-%m-%d")
                fecha_ini = datetime.strptime(fecha_inicio, "%Y-%m-%d")
                if fecha_row < fecha_ini:
                    continue
            if fecha_fin:
                fecha_row = datetime.strptime(row["fecha"], "%Y-%m-%d")
                fecha_final = datetime.strptime(fecha_fin, "%Y-%m-%d")
                if fecha_row > fecha_final:
                    continue
            resultados.append(row)
    return resultados
import csv
from datetime import datetime

HISTORIAL_PATH = "historial_entrenamientos.csv"

CAMPOS = [
    "usuario_id",
    "fecha",
    "tipo",
    "nombre_entrenamiento",
    "carga",
    "duracion",
    "distancia",
    "frecuencia_cardiaca_media",
    "frecuencia_cardiaca_maxima",
    "zona_entrenamiento",
    "comentarios"
]

def guardar_entrenamiento_historial(
    usuario_id,
    fecha,
    tipo,
    nombre_entrenamiento,
    carga,
    duracion,
    distancia,
    frecuencia_cardiaca_media,
    frecuencia_cardiaca_maxima,
    zona_entrenamiento="",
    comentarios=""
):
    """
    Guarda un entrenamiento en el historial CSV.
    """
    fila = {
        "usuario_id": usuario_id,
        "fecha": fecha,
        "tipo": tipo,
        "nombre_entrenamiento": nombre_entrenamiento,
        "carga": carga,
        "duracion": duracion,
        "distancia": distancia,
        "frecuencia_cardiaca_media": frecuencia_cardiaca_media,
        "frecuencia_cardiaca_maxima": frecuencia_cardiaca_maxima,
        "zona_entrenamiento": zona_entrenamiento,
        "comentarios": comentarios
    }
    with open(HISTORIAL_PATH, "a", newline='', encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CAMPOS)
        writer.writerow(fila)

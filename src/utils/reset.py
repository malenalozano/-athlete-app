from pathlib import Path
from db.db_manager import get_db_connection, init_db


def reset_total_datos():
	conn = get_db_connection()
	tablas = [
		"actividades_garmin",
		"diario_fisiologia",
		"entrenamientos_fuerza",
		"sesiones_fuerza",
		"ejercicios_fuerza",
		"datos_sueno",
		"datos_biometricos_premium",
		"historial_lesiones",
		"estudios_referencia",
		"plan_entrenamiento",
		"usuarios",
	]

	try:
		for tabla in tablas:
			conn.execute(f"DELETE FROM {tabla}")
		# Reinicia contadores autoincrement cuando aplique.
		try:
			conn.execute("DELETE FROM sqlite_sequence")
		except Exception:
			pass
		conn.commit()
	except Exception:
		conn.rollback()
		raise
	finally:
		conn.close()

	# Limpia archivos locales de estudios subidos y el último usuario recordado.
	studies_dir = Path(__file__).resolve().parent / "uploaded_studies"
	if studies_dir.exists():
		for p in studies_dir.glob("*"):
			if p.is_file():
				p.unlink(missing_ok=True)

	last_user_file = Path.home() / ".athlete_last_user"
	if last_user_file.exists():
		last_user_file.unlink(missing_ok=True)


if __name__ == "__main__":
	init_db()
	reset_total_datos()
	print("Reset completo: datos borrados y sesión inicial lista para primer login.")

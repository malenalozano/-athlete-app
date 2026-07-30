"""
Tareas programadas (background jobs).

Job activo:
  - daily_sync_and_reminder — todos los días a las 09:00 hora Madrid
    → Sincroniza Garmin (actividades + biométricos) de todos los usuarios y,
      justo después, envía la notificación ntfy con el plan del día.

EN PRODUCCIÓN (Render): el scheduler interno está DESACTIVADO porque el dyno
free duerme. El job lo dispara cron-job.org llamando a:
  - 09:00 → POST https://tu-backend.onrender.com/tasks/daily
con header X-Cron-Secret: <valor de CRON_SECRET en las env vars de Render>.
Ese mismo endpoint hace sync + recordatorio, así que basta con UN cron job
diario a las 9am (no hace falta configurar /tasks/garmin-sync aparte).
"""
import logging
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from database import get_db
from notifications import send_notification
from config import settings

logger = logging.getLogger(__name__)

# ── Emojis por tipo de sesión ──────────────────────────────────────────────────
_EMOJI_TIPO = {
    "carrera":  "🏃",
    "fuerza":   "💪",
    "descanso": "😴",
    "cross":    "🚴",
    "yoga":     "🧘",
    "natacion": "🏊",
}

_EMOJI_INTENSIDAD = {
    "suave":   "🟢",
    "medio":   "🟡",
    "fuerte":  "🔴",
    "alta":    "🔴",
    "baja":    "🟢",
    "media":   "🟡",
}


def _emoji_sesion(tipo: str, intensidad: str | None) -> str:
    tipo_lower = (tipo or "").lower()
    for key, emoji in _EMOJI_TIPO.items():
        if key in tipo_lower:
            return emoji
    return _EMOJI_INTENSIDAD.get((intensidad or "").lower(), "📋")


def _formato_sesion(row: dict) -> str:
    """Formatea una sesión del plan en texto legible para la notificación."""
    partes = []

    emoji = _emoji_sesion(row["tipo"], row["intensidad"])
    nombre = row["sesion"] or row["tipo"] or "Sesión"
    partes.append(f"{emoji} {nombre}")

    if row.get("km_planificados"):
        partes.append(f"{row['km_planificados']} km")

    if row.get("duracion_min"):
        h = row["duracion_min"] // 60
        m = row["duracion_min"] % 60
        partes.append(f"{h}h {m}min" if h else f"{m} min")

    if row.get("intensidad"):
        partes.append(f"Intensidad: {row['intensidad']}")

    if row.get("detalles"):
        # Truncar detalles largos
        det = row["detalles"]
        if len(det) > 120:
            det = det[:117] + "..."
        partes.append(f"\n📝 {det}")

    return " · ".join(partes[:3]) + (partes[3] if len(partes) > 3 else "")


def sync_all_users() -> list[dict]:
    """Sincroniza Garmin (actividades + biométricos) para todos los usuarios con
    tokens guardados. Un usuario que falle (tokens caídos, 429, timeout...) no
    interrumpe la sync del resto — cada uno se aísla en su propio try/except.
    """
    from database import get_db
    try:
        # Importación lazy para evitar circular imports
        import sys, os
        _routers_path = os.path.join(os.path.dirname(__file__))
        if _routers_path not in sys.path:
            sys.path.insert(0, _routers_path)
        from routers.garmin import _do_sync
    except Exception as e:
        logger.error(f"No se pudo importar _do_sync para auto-sync Garmin: {e}")
        return []

    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT id, nombre FROM usuarios WHERE garmin_tokens IS NOT NULL AND garmin_tokens != ''"
        ).fetchall()
    finally:
        conn.close()

    resultados = []
    for usuario_id, nombre in rows:
        try:
            res = _do_sync(usuario_id)
            acts = res.get("actividades_importadas", 0)
            logger.info(f"Auto-sync Garmin OK para {nombre}: {acts} actividad(es)")
            resultados.append({"usuario": nombre, "ok": True, "actividades": acts})
        except Exception as e:
            logger.warning(f"Auto-sync Garmin ERROR para {nombre}: {e}")
            resultados.append({"usuario": nombre, "ok": False, "error": str(e)[:150]})
    return resultados


def daily_training_reminder():
    """Envía la sesión de hoy a las 9:00 vía ntfy."""
    if not settings.ntfy_topic:
        logger.debug("NTFY_TOPIC no configurado — job omitido.")
        return

    hoy = date.today().isoformat()
    conn = get_db()

    try:
        # Solo traemos el usuario_id=1 (Malena) porque NTFY_TOPIC es personal.
        # Si en el futuro Dani quiere notificaciones, añadir ntfy_topic a la tabla usuarios.
        rows = conn.execute(
            """SELECT u.nombre, p.tipo, p.sesion, p.detalles,
                      p.duracion_min, p.intensidad, p.km_planificados, p.completado
               FROM plan_entrenamiento p
               JOIN usuarios u ON u.id = p.usuario_id
               WHERE p.fecha = ? AND p.usuario_id = 1
               ORDER BY p.id""",
            (hoy,),
        ).fetchall()
    finally:
        conn.close()

    cols = ["nombre", "tipo", "sesion", "detalles",
            "duracion_min", "intensidad", "km_planificados", "completado"]
    sesiones = [dict(zip(cols, r)) for r in rows]

    if not sesiones:
        send_notification(
            "No hay sesiones programadas para hoy. Dia de descanso! 🛌",
            title="Plan de hoy",
            tags=["calendar", "zzz"],
            priority="low",
        )
        return

    # Agrupar por usuario (en caso de varios)
    from collections import defaultdict
    por_usuario: dict[str, list] = defaultdict(list)
    for s in sesiones:
        por_usuario[s["nombre"]].append(s)

    for nombre, sesiones_usuario in por_usuario.items():
        lineas = []
        for s in sesiones_usuario:
            if s.get("completado"):
                lineas.append(f"✅ {s['sesion'] or s['tipo']} (completada)")
            else:
                lineas.append(_formato_sesion(s))

        texto = "\n".join(lineas)
        n_sesiones = len(sesiones_usuario)
        subtitle = f"{n_sesiones} sesión" if n_sesiones == 1 else f"{n_sesiones} sesiones"

        send_notification(
            texto,
            title=f"Plan de hoy — {subtitle}",
            tags=["calendar", "runner"],
            priority="default",
        )
        logger.info(f"Recordatorio diario enviado para {nombre}: {n_sesiones} sesión(es)")


def daily_sync_and_reminder():
    """09:00 Madrid — sincroniza Garmin de todos los usuarios y, justo después,
    envía el recordatorio del plan de hoy (ya con los datos recién sincronizados)."""
    sync_all_users()
    daily_training_reminder()


# ── Inicialización del scheduler ───────────────────────────────────────────────

_scheduler: BackgroundScheduler | None = None


def start_scheduler():
    """
    Inicia el scheduler solo si está corriendo en local (no en Render/Railway).
    En producción con plan gratuito el servidor duerme, así que el scheduler
    no es fiable — usamos cron-job.org para llamar al endpoint /notificaciones/test-hoy.
    """
    global _scheduler

    import os
    # Render inyecta RENDER=true; Railway inyecta RAILWAY_ENVIRONMENT
    en_produccion = os.getenv("RENDER") or os.getenv("RAILWAY_ENVIRONMENT")
    if en_produccion:
        logger.info("Scheduler interno desactivado en producción (usa cron-job.org).")
        return

    if _scheduler and _scheduler.running:
        return

    _scheduler = BackgroundScheduler(timezone="Europe/Madrid")

    # ── Job único: sync Garmin + recordatorio a las 09:00 (solo en local) ──
    _scheduler.add_job(
        daily_sync_and_reminder,
        trigger=CronTrigger(hour=9, minute=0, timezone="Europe/Madrid"),
        id="daily_sync_and_reminder",
        name="Sync Garmin + recordatorio diario",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("Scheduler iniciado — sync Garmin + recordatorio a las 09:00 (Madrid)")


def stop_scheduler():
    """Detiene el scheduler. Llamar desde el shutdown de FastAPI."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido.")

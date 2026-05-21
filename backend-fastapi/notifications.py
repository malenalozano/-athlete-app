"""
Módulo de notificaciones via ntfy.sh
Uso: send_notification("¡Sync Garmin completada!", title="Athlete App", tags=["white_check_mark"])

Para recibirlas en tu iPhone:
1. Instala la app "ntfy" desde App Store
2. Suscríbete al topic configurado en NTFY_TOPIC (en .env)
"""
import logging
import requests
from config import settings

logger = logging.getLogger(__name__)


def send_notification(
    message: str,
    *,
    title: str = "Athlete App",
    tags: list[str] | None = None,
    priority: str = "default",  # min | low | default | high | urgent
) -> bool:
    """
    Envía una notificación push a tu iPhone via ntfy.sh.

    Args:
        message: Texto principal de la notificación.
        title:   Título (aparece en negrita).
        tags:    Lista de emojis/tags ntfy, ej. ["white_check_mark", "runner"].
        priority: Nivel de prioridad ntfy.

    Returns:
        True si se envió correctamente, False en caso de error.
    """
    topic = settings.ntfy_topic
    if not topic:
        logger.debug("NTFY_TOPIC no configurado — notificación omitida.")
        return False

    url = f"https://ntfy.sh/{topic}"
    headers = {
        "Title": title,
        "Priority": priority,
        "Content-Type": "text/plain; charset=utf-8",
    }
    if tags:
        headers["Tags"] = ",".join(tags)

    try:
        # Los headers HTTP solo admiten ASCII — quitamos emojis del título
        title_ascii = title.encode("ascii", errors="ignore").decode("ascii").strip()
        if not title_ascii:
            title_ascii = "Athlete App"
        headers["Title"] = title_ascii

        resp = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=5)
        resp.raise_for_status()
        logger.info(f"Notificación enviada a ntfy.sh/{topic}: {title} — {message}")
        return True
    except Exception as e:
        logger.warning(f"Error enviando notificación ntfy: {e}")
        return False

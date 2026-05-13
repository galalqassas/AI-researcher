"""Pipeline alerting via webhook (supports Slack incoming hooks and generic endpoints)."""

import logging
import requests
from app.config import WEBHOOK_URL

log = logging.getLogger(__name__)


def send_alert(title: str, message: str, status: str = "success"):
    """Send a notification to the configured webhook URL.

    Posts a JSON payload compatible with Slack incoming hooks and generic
    webhook receivers. Silently skips if WEBHOOK_URL is not configured.
    """
    if not WEBHOOK_URL:
        return

    payload = {
        "text": f"[Auto-Researcher] {title}",
        "title": title,
        "message": message,
        "status": status,
    }

    try:
        resp = requests.post(
            WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        log.info(f"Alert sent: {title}")
    except Exception as e:
        log.warning(f"Failed to send alert: {e}")
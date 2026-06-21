import json
import logging

from pydantic import ValidationError

import metrics
from db import DB
from validator import parse_event

logger = logging.getLogger(__name__)


class UserEvent:
    @staticmethod
    def save_user_event(ch, method, properties, body: bytes):
        # --- Deserialise -------------------------------------------------
        try:
            payload = json.loads(body)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON — rejecting without requeue: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            metrics.increment_error("unknown", "validation")
            return

        event_type = payload.get("event", "unknown")

        # --- Validate ----------------------------------------------------
        try:
            parsed = parse_event(payload)
        except (ValidationError, ValueError) as exc:
            logger.error("Validation error — rejecting without requeue: %s", exc)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            metrics.increment_error(event_type, "validation")
            return

        user_id = str(getattr(parsed, "user_id", ""))

        # --- Persist -----------------------------------------------------
        db = DB()
        try:
            db.insert_event(event_type, user_id, payload)
            ch.basic_ack(delivery_tag=method.delivery_tag)
            logger.info("Saved event=%s user_id=%s", event_type, user_id)
            metrics.increment_event(event_type)
        except Exception as exc:
            requeue = not method.redelivered
            logger.error(
                "MongoDB error for event=%s user_id=%s: %s — %s",
                event_type, user_id, exc,
                "requeueing" if requeue else "sending to DLQ",
            )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=requeue)
            metrics.increment_error(event_type, "db")
        finally:
            db.close()

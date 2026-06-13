import logging

from pydantic import ValidationError

from db import DB
from metrics import increment_event, increment_error
from validator import parse_event

log = logging.getLogger(__name__)


def process_message(raw: dict, db: DB) -> None:
    """Validate, persist, and record metrics for one user event.

    Raises:
        ValueError: unknown schema_version or event type
        pydantic.ValidationError: payload does not match the model
        Exception: MongoDB write failure
    """
    event_type = raw.get("event", "unknown")

    try:
        parsed = parse_event(raw)
    except ValidationError:
        increment_error(event_type, "validation")
        raise
    except ValueError as exc:
        reason = "unknown_schema" if "schema_version" in str(exc) else "validation"
        increment_error(event_type, reason)
        raise

    user_id = str(getattr(parsed, "user_id", ""))

    try:
        db.insert_event(event_type, user_id, raw)
        db.upsert_user_state(event_type, user_id, parsed)
    except Exception:
        increment_error(event_type, "db")
        raise

    increment_event(event_type)
    log.info("Processed event=%s user_id=%s", event_type, user_id)

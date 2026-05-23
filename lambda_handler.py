import base64
import json
import logging

from db import DB
from handler import process_message

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_db: DB | None = None


def _get_db() -> DB:
    global _db
    if _db is None:
        _db = DB()
    return _db


def handler(event: dict, context) -> dict:
    """AWS Lambda entry point for Amazon MQ and SQS triggers.

    Amazon MQ event keys:  event["rmqMessagesByQueue"][queue_key][*]["data"] (base64)
    SQS event keys:        event["Records"][*]["body"] (JSON string)
    """
    db = _get_db()
    failed = 0
    total = 0

    if "rmqMessagesByQueue" in event:
        for messages in event["rmqMessagesByQueue"].values():
            for msg in messages:
                total += 1
                try:
                    body = base64.b64decode(msg["data"]).decode("utf-8")
                    process_message(json.loads(body), db)
                except Exception as exc:
                    log.error("Failed to process Amazon MQ message: %s", exc)
                    failed += 1

    elif "Records" in event:
        total = len(event["Records"])
        for record in event["Records"]:
            try:
                process_message(json.loads(record["body"]), db)
            except Exception as exc:
                log.error("Failed to process SQS record: %s", exc)
                failed += 1

    return {"processed": total - failed, "failed": failed}

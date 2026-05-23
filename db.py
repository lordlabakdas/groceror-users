import logging
from datetime import datetime, timezone

from pymongo import MongoClient

import config

log = logging.getLogger(__name__)

_TOP_LEVEL_FIELDS = ("phone", "entity_type", "profile_id", "name", "email", "location")


class DB:
    def __init__(self):
        self.client = MongoClient(config.MONGO_URI)
        self.db = self.client["users"]

    def insert_event(self, event_type: str, user_id: str, raw_payload: dict) -> None:
        collection = self.db["user_events"]
        doc: dict = {
            "event": event_type,
            "schema_version": raw_payload.get("schema_version", "1.0"),
            "user_id": user_id,
            "received_at": datetime.now(timezone.utc).isoformat(),
            "raw_payload": raw_payload,
        }
        for field in _TOP_LEVEL_FIELDS:
            if field in raw_payload:
                doc[field] = raw_payload[field]
        result = collection.insert_one(doc)
        log.info("Inserted event=%s user_id=%s _id=%s", event_type, user_id, result.inserted_id)

    def close(self) -> None:
        self.client.close()

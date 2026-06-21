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
        self.collection = self.db["user_events"]
        self.collection.create_index([("user_id", 1), ("event", 1)])
        self.db["users"].create_index([("user_id", 1)], unique=True)

    def insert_event(self, event_type: str, user_id: str, raw_payload: dict) -> None:
        collection = self.db["user_events"]
        doc: dict = {
            "event": event_type,
            "schema_version": raw_payload.get("schema_version", "1.0"),
            "user_id": user_id,
            "received_at": datetime.now(timezone.utc),
            "raw_payload": raw_payload,
        }
        for field in _TOP_LEVEL_FIELDS:
            if field in raw_payload:
                doc[field] = raw_payload[field]
        result = collection.insert_one(doc)
        log.info("Inserted event=%s user_id=%s _id=%s", event_type, user_id, result.inserted_id)

    def upsert_user_state(self, event_type: str, user_id: str, parsed_event) -> None:
        """Update the current state of a user based on the incoming event.

        Uses upsert so events can arrive for users not yet in the collection
        (e.g. otp_verified before user_registered due to redelivery).
        """
        now = datetime.now(timezone.utc)
        set_fields: dict = {"last_event": event_type, "updated_at": now}
        set_on_insert: dict = {"user_id": user_id, "registered_at": now}

        if event_type == "user_registered":
            set_fields.update({
                "phone": parsed_event.phone,
                "entity_type": parsed_event.entity_type,
                "status": "registered",
            })
            set_on_insert["registered_at"] = now
        elif event_type == "otp_verified":
            set_fields.update({
                "status": "otp_verified",
                "otp_verified_at": now,
                "phone": parsed_event.phone,
            })
        elif event_type == "profile_updated":
            set_fields.update({
                "status": "active",
                "profile_id": parsed_event.profile_id,
                "entity_type": parsed_event.entity_type,
                "profile_updated_at": now,
            })
            for field in ("name", "email", "location"):
                val = getattr(parsed_event, field, None)
                if val is not None:
                    set_fields[field] = val
        elif event_type == "password_changed":
            set_fields["password_changed_at"] = now
        else:
            return

        result = self.db["users"].update_one(
            {"user_id": user_id},
            {"$set": set_fields, "$setOnInsert": set_on_insert},
            upsert=True,
        )
        log.info(
            "Upserted user state event=%s user_id=%s upserted=%s",
            event_type, user_id, result.upserted_id is not None,
        )

    def get_collection(self, name: str):
        return self.db[name]

    def close(self) -> None:
        self.client.close()

import logging
from typing import List

from db import DB

logger = logging.getLogger(__name__)

EVENTS_COLLECTION = "user_events"
USERS_COLLECTION = "users"


class UserAnalytics:

    def __init__(self, db: DB):
        self._events = db.get_collection(EVENTS_COLLECTION)
        self._users = db.get_collection(USERS_COLLECTION)

    def total_users(self) -> int:
        return self._users.count_documents({})

    def active_users(self) -> int:
        return self._users.count_documents({"status": "active"})

    def users_by_entity_type(self) -> List[dict]:
        pipeline = [
            {"$group": {"_id": "$entity_type", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$project": {"entity_type": "$_id", "count": 1, "_id": 0}},
        ]
        return list(self._users.aggregate(pipeline))

    def event_counts(self) -> dict:
        pipeline = [
            {"$group": {"_id": "$event", "count": {"$sum": 1}}},
            {"$project": {"event": "$_id", "count": 1, "_id": 0}},
        ]
        return {r["event"]: r["count"] for r in self._events.aggregate(pipeline)}

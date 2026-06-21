import logging
from typing import List

from db import DB

logger = logging.getLogger(__name__)

COLLECTION = "user_events"


class UserPerDayAnalytics:

    def __init__(self, db: DB):
        self._col = db.get_collection(COLLECTION)

    def registrations_per_day(self, limit: int = 30) -> List[dict]:
        """Return new user registrations grouped by day, most recent first.

        ``received_at`` is stored as a UTC datetime object, so no string
        conversion is needed before grouping.
        """
        pipeline = [
            {"$match": {"event": "user_registered"}},
            {
                "$group": {
                    "_id": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$received_at"}
                    },
                    "registrations": {"$sum": 1},
                }
            },
            {"$sort": {"_id": -1}},
            {"$limit": limit},
            {"$project": {"date": "$_id", "registrations": 1, "_id": 0}},
        ]
        return list(self._col.aggregate(pipeline))

    def events_per_day(self, limit: int = 30) -> List[dict]:
        """Return all event types grouped by day, most recent first."""
        pipeline = [
            {
                "$group": {
                    "_id": {
                        "date": {
                            "$dateToString": {"format": "%Y-%m-%d", "date": "$received_at"}
                        },
                        "event": "$event",
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.date": -1}},
            {"$limit": limit},
            {
                "$project": {
                    "date": "$_id.date",
                    "event": "$_id.event",
                    "count": 1,
                    "_id": 0,
                }
            },
        ]
        return list(self._col.aggregate(pipeline))

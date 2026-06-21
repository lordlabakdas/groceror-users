from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import mongomock
import pytest

from analytics.user_analytics import UserAnalytics
from analytics.user_per_day_analytics import UserPerDayAnalytics
from db import DB


@pytest.fixture
def mock_db():
    with patch("db.MongoClient", mongomock.MongoClient):
        yield DB()


def _dt(days_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


def _insert_event(db, event: str, user_id: str, days_ago: int = 0):
    db.db["user_events"].insert_one({
        "event": event,
        "user_id": user_id,
        "received_at": _dt(days_ago),
        "schema_version": "1.0",
    })


def _insert_user(db, user_id: str, status: str = "active", entity_type: str = "user"):
    db.db["users"].insert_one({
        "user_id": user_id,
        "status": status,
        "entity_type": entity_type,
        "registered_at": _dt(),
    })


# ---------------------------------------------------------------------------
# UserAnalytics
# ---------------------------------------------------------------------------

class TestUserAnalytics:

    def test_total_users_empty(self, mock_db):
        assert UserAnalytics(mock_db).total_users() == 0

    def test_total_users_counts_all(self, mock_db):
        _insert_user(mock_db, "u1")
        _insert_user(mock_db, "u2")
        assert UserAnalytics(mock_db).total_users() == 2

    def test_active_users_filters_by_status(self, mock_db):
        _insert_user(mock_db, "u1", status="active")
        _insert_user(mock_db, "u2", status="registered")
        _insert_user(mock_db, "u3", status="active")
        assert UserAnalytics(mock_db).active_users() == 2

    def test_active_users_empty(self, mock_db):
        _insert_user(mock_db, "u1", status="registered")
        assert UserAnalytics(mock_db).active_users() == 0

    def test_users_by_entity_type(self, mock_db):
        _insert_user(mock_db, "u1", entity_type="user")
        _insert_user(mock_db, "u2", entity_type="user")
        _insert_user(mock_db, "u3", entity_type="store")
        result = UserAnalytics(mock_db).users_by_entity_type()
        by_type = {r["entity_type"]: r["count"] for r in result}
        assert by_type["user"] == 2
        assert by_type["store"] == 1

    def test_users_by_entity_type_empty(self, mock_db):
        assert UserAnalytics(mock_db).users_by_entity_type() == []

    def test_event_counts(self, mock_db):
        _insert_event(mock_db, "user_registered", "u1")
        _insert_event(mock_db, "user_registered", "u2")
        _insert_event(mock_db, "otp_verified", "u1")
        counts = UserAnalytics(mock_db).event_counts()
        assert counts["user_registered"] == 2
        assert counts["otp_verified"] == 1

    def test_event_counts_empty(self, mock_db):
        assert UserAnalytics(mock_db).event_counts() == {}


# ---------------------------------------------------------------------------
# UserPerDayAnalytics
# ---------------------------------------------------------------------------

class TestUserPerDayAnalytics:

    def test_registrations_per_day_empty(self, mock_db):
        assert UserPerDayAnalytics(mock_db).registrations_per_day() == []

    def test_registrations_per_day_counts_only_user_registered(self, mock_db):
        _insert_event(mock_db, "user_registered", "u1", days_ago=0)
        _insert_event(mock_db, "user_registered", "u2", days_ago=0)
        _insert_event(mock_db, "otp_verified", "u1", days_ago=0)
        result = UserPerDayAnalytics(mock_db).registrations_per_day()
        assert len(result) == 1
        assert result[0]["registrations"] == 2

    def test_registrations_per_day_groups_by_date(self, mock_db):
        _insert_event(mock_db, "user_registered", "u1", days_ago=0)
        _insert_event(mock_db, "user_registered", "u2", days_ago=1)
        _insert_event(mock_db, "user_registered", "u3", days_ago=1)
        result = UserPerDayAnalytics(mock_db).registrations_per_day()
        assert len(result) == 2
        counts = {r["date"]: r["registrations"] for r in result}
        today = _dt(0).strftime("%Y-%m-%d")
        yesterday = _dt(1).strftime("%Y-%m-%d")
        assert counts[today] == 1
        assert counts[yesterday] == 2

    def test_registrations_per_day_most_recent_first(self, mock_db):
        _insert_event(mock_db, "user_registered", "u1", days_ago=2)
        _insert_event(mock_db, "user_registered", "u2", days_ago=0)
        result = UserPerDayAnalytics(mock_db).registrations_per_day()
        assert result[0]["date"] > result[1]["date"]

    def test_registrations_per_day_limit(self, mock_db):
        for i in range(5):
            _insert_event(mock_db, "user_registered", f"u{i}", days_ago=i)
        result = UserPerDayAnalytics(mock_db).registrations_per_day(limit=3)
        assert len(result) == 3

    def test_events_per_day_empty(self, mock_db):
        assert UserPerDayAnalytics(mock_db).events_per_day() == []

    def test_events_per_day_groups_by_date_and_event(self, mock_db):
        _insert_event(mock_db, "user_registered", "u1", days_ago=0)
        _insert_event(mock_db, "otp_verified", "u1", days_ago=0)
        _insert_event(mock_db, "user_registered", "u2", days_ago=0)
        result = UserPerDayAnalytics(mock_db).events_per_day()
        today = _dt(0).strftime("%Y-%m-%d")
        today_results = [r for r in result if r["date"] == today]
        by_event = {r["event"]: r["count"] for r in today_results}
        assert by_event["user_registered"] == 2
        assert by_event["otp_verified"] == 1

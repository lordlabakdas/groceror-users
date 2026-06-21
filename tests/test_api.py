from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import mongomock
import pytest
from fastapi.testclient import TestClient

from api import app
from db import DB

client = TestClient(app)


def _make_mock_db():
    mock_client = mongomock.MongoClient()
    mongo_db = mock_client["users"]
    mock_db = MagicMock()
    mock_db.get_collection.side_effect = lambda name: mongo_db[name]
    mock_db.close = MagicMock()
    return mock_db


def _dt(days_ago: int = 0) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days_ago)


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# /metrics
# ---------------------------------------------------------------------------

def test_metrics_returns_prometheus_text():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "groceror_users_events_total" in resp.text
    assert resp.headers["content-type"].startswith("text/plain")


# ---------------------------------------------------------------------------
# /analytics/summary
# ---------------------------------------------------------------------------

def test_summary_returns_200():
    mock_db = _make_mock_db()
    with patch("api.DB", return_value=mock_db):
        resp = client.get("/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "active_users" in data
    assert "users_by_entity_type" in data
    assert "event_counts" in data


def test_summary_with_data():
    mock_db = _make_mock_db()
    mock_db.get_collection("users").insert_many([
        {"user_id": "u1", "status": "active", "entity_type": "user"},
        {"user_id": "u2", "status": "registered", "entity_type": "store"},
    ])
    mock_db.get_collection("user_events").insert_many([
        {"event": "user_registered", "user_id": "u1", "received_at": _dt()},
        {"event": "user_registered", "user_id": "u2", "received_at": _dt()},
        {"event": "otp_verified", "user_id": "u1", "received_at": _dt()},
    ])
    with patch("api.DB", return_value=mock_db):
        resp = client.get("/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_users"] == 2
    assert data["active_users"] == 1
    assert data["event_counts"]["user_registered"] == 2
    assert data["event_counts"]["otp_verified"] == 1


# ---------------------------------------------------------------------------
# /analytics/registrations-per-day
# ---------------------------------------------------------------------------

def test_registrations_per_day_returns_200():
    mock_db = _make_mock_db()
    with patch("api.DB", return_value=mock_db):
        resp = client.get("/analytics/registrations-per-day")
    assert resp.status_code == 200
    assert "days" in resp.json()
    assert isinstance(resp.json()["days"], list)


def test_registrations_per_day_with_data():
    mock_db = _make_mock_db()
    col = mock_db.get_collection("user_events")
    col.insert_many([
        {"event": "user_registered", "user_id": "u1", "received_at": _dt(0)},
        {"event": "user_registered", "user_id": "u2", "received_at": _dt(0)},
        {"event": "otp_verified", "user_id": "u1", "received_at": _dt(0)},
    ])
    with patch("api.DB", return_value=mock_db):
        resp = client.get("/analytics/registrations-per-day")
    days = resp.json()["days"]
    assert len(days) == 1
    assert days[0]["registrations"] == 2


def test_registrations_per_day_respects_limit():
    mock_db = _make_mock_db()
    col = mock_db.get_collection("user_events")
    for i in range(5):
        col.insert_one({"event": "user_registered", "user_id": f"u{i}", "received_at": _dt(i)})
    with patch("api.DB", return_value=mock_db):
        resp = client.get("/analytics/registrations-per-day?limit=2")
    assert len(resp.json()["days"]) == 2


# ---------------------------------------------------------------------------
# /analytics/events-per-day
# ---------------------------------------------------------------------------

def test_events_per_day_returns_200():
    mock_db = _make_mock_db()
    with patch("api.DB", return_value=mock_db):
        resp = client.get("/analytics/events-per-day")
    assert resp.status_code == 200
    assert "days" in resp.json()


def test_events_per_day_with_data():
    mock_db = _make_mock_db()
    col = mock_db.get_collection("user_events")
    col.insert_many([
        {"event": "user_registered", "user_id": "u1", "received_at": _dt(0)},
        {"event": "otp_verified", "user_id": "u1", "received_at": _dt(0)},
        {"event": "profile_updated", "user_id": "u1", "received_at": _dt(1)},
    ])
    with patch("api.DB", return_value=mock_db):
        resp = client.get("/analytics/events-per-day")
    days = resp.json()["days"]
    today = _dt(0).strftime("%Y-%m-%d")
    today_entries = [d for d in days if d["date"] == today]
    by_event = {d["event"]: d["count"] for d in today_entries}
    assert by_event["user_registered"] == 1
    assert by_event["otp_verified"] == 1

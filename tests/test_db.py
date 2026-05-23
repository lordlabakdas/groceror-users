import mongomock
import pytest
from unittest.mock import patch
from db import DB


@pytest.fixture
def db():
    with patch("db.MongoClient", mongomock.MongoClient):
        yield DB()


def test_insert_event_stores_document(db):
    raw = {
        "schema_version": "1.0",
        "event": "user_registered",
        "user_id": "uid-1",
        "phone": "+1",
        "entity_type": "user",
    }
    db.insert_event("user_registered", "uid-1", raw)
    collection = db.db["user_events"]
    docs = list(collection.find({"user_id": "uid-1"}))
    assert len(docs) == 1
    assert docs[0]["event"] == "user_registered"
    assert docs[0]["phone"] == "+1"
    assert "received_at" in docs[0]
    assert docs[0]["raw_payload"] == raw


def test_insert_event_is_append_only(db):
    raw = {"schema_version": "1.0", "event": "otp_verified", "user_id": "uid-2", "phone": "+2"}
    db.insert_event("otp_verified", "uid-2", raw)
    db.insert_event("otp_verified", "uid-2", raw)
    docs = list(db.db["user_events"].find({"user_id": "uid-2"}))
    assert len(docs) == 2


def test_insert_event_copies_top_level_fields(db):
    raw = {
        "schema_version": "1.0",
        "event": "profile_updated",
        "user_id": "uid-3",
        "profile_id": "prof-1",
        "entity_type": "store",
        "name": "Shop",
        "email": "shop@x.com",
        "location": "LA",
    }
    db.insert_event("profile_updated", "uid-3", raw)
    doc = db.db["user_events"].find_one({"user_id": "uid-3"})
    assert doc["name"] == "Shop"
    assert doc["entity_type"] == "store"
    assert doc["location"] == "LA"

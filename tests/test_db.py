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


# --- upsert_user_state tests ---

from types import SimpleNamespace


def test_upsert_user_state_registered_creates_user(db):
    parsed = SimpleNamespace(phone="+1", entity_type="user")
    db.upsert_user_state("user_registered", "uid-10", parsed)
    user = db.db["users"].find_one({"user_id": "uid-10"})
    assert user is not None
    assert user["status"] == "registered"
    assert user["phone"] == "+1"
    assert user["entity_type"] == "user"
    assert "registered_at" in user


def test_upsert_user_state_otp_verified_advances_status(db):
    parsed_reg = SimpleNamespace(phone="+1", entity_type="user")
    db.upsert_user_state("user_registered", "uid-11", parsed_reg)

    parsed_otp = SimpleNamespace(phone="+1")
    db.upsert_user_state("otp_verified", "uid-11", parsed_otp)

    user = db.db["users"].find_one({"user_id": "uid-11"})
    assert user["status"] == "otp_verified"
    assert "otp_verified_at" in user
    assert user["last_event"] == "otp_verified"


def test_upsert_user_state_profile_updated_sets_active_and_fields(db):
    parsed = SimpleNamespace(
        profile_id="prof-1", entity_type="user", name="Alice", email="a@x.com", location="NY"
    )
    db.upsert_user_state("profile_updated", "uid-12", parsed)

    user = db.db["users"].find_one({"user_id": "uid-12"})
    assert user["status"] == "active"
    assert user["name"] == "Alice"
    assert user["email"] == "a@x.com"
    assert user["location"] == "NY"
    assert user["profile_id"] == "prof-1"
    assert "profile_updated_at" in user


def test_upsert_user_state_profile_updated_skips_none_fields(db):
    parsed = SimpleNamespace(
        profile_id="prof-2", entity_type="store", name="Shop", email=None, location=None
    )
    db.upsert_user_state("profile_updated", "uid-13", parsed)

    user = db.db["users"].find_one({"user_id": "uid-13"})
    assert user["name"] == "Shop"
    assert "email" not in user
    assert "location" not in user


def test_upsert_user_state_password_changed_sets_timestamp(db):
    parsed_reg = SimpleNamespace(phone="+5", entity_type="user")
    db.upsert_user_state("user_registered", "uid-14", parsed_reg)

    parsed_pw = SimpleNamespace()
    db.upsert_user_state("password_changed", "uid-14", parsed_pw)

    user = db.db["users"].find_one({"user_id": "uid-14"})
    assert "password_changed_at" in user
    assert user["last_event"] == "password_changed"


def test_upsert_user_state_is_idempotent_on_redelivery(db):
    parsed = SimpleNamespace(phone="+6", entity_type="user")
    db.upsert_user_state("user_registered", "uid-15", parsed)
    db.upsert_user_state("user_registered", "uid-15", parsed)

    assert db.db["users"].count_documents({"user_id": "uid-15"}) == 1


def test_upsert_user_state_unknown_event_is_noop(db):
    parsed = SimpleNamespace()
    db.upsert_user_state("unknown_event", "uid-16", parsed)
    assert db.db["users"].find_one({"user_id": "uid-16"}) is None

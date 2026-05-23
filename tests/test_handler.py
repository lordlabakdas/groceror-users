import pytest
from unittest.mock import patch, MagicMock
from pydantic import ValidationError

from handler import process_message


RAW_REGISTERED = {
    "schema_version": "1.0",
    "event": "user_registered",
    "user_id": "uid-1",
    "phone": "+1",
    "entity_type": "user",
}
RAW_OTP = {
    "schema_version": "1.0",
    "event": "otp_verified",
    "user_id": "uid-2",
    "phone": "+2",
}
RAW_PROFILE = {
    "schema_version": "1.0",
    "event": "profile_updated",
    "user_id": "uid-3",
    "profile_id": "prof-1",
    "entity_type": "user",
    "name": "Bob",
    "email": "bob@x.com",
    "location": "LA",
}
RAW_PASSWORD = {
    "schema_version": "1.0",
    "event": "password_changed",
    "user_id": "uid-4",
    "phone": "+4",
}


def test_process_message_inserts_to_db(mock_db):
    with patch("handler.increment_event"), patch("handler.increment_error"):
        process_message(RAW_REGISTERED, mock_db)
    docs = list(mock_db.db["user_events"].find({"user_id": "uid-1"}))
    assert len(docs) == 1
    assert docs[0]["event"] == "user_registered"


def test_process_message_increments_event_counter(mock_db):
    with patch("handler.increment_event") as mock_inc, patch("handler.increment_error"):
        process_message(RAW_OTP, mock_db)
    mock_inc.assert_called_once_with("otp_verified")


def test_process_message_handles_all_event_types(mock_db):
    with patch("handler.increment_event"), patch("handler.increment_error"):
        for raw in [RAW_REGISTERED, RAW_OTP, RAW_PROFILE, RAW_PASSWORD]:
            process_message(raw, mock_db)
    assert mock_db.db["user_events"].count_documents({}) == 4


def test_process_message_unknown_schema_raises_and_increments_error(mock_db):
    with patch("handler.increment_error") as mock_err:
        with pytest.raises(ValueError):
            process_message({"schema_version": "9.9", "event": "user_registered"}, mock_db)
    mock_err.assert_called_once_with("user_registered", "unknown_schema")


def test_process_message_validation_error_raises_and_increments_error(mock_db):
    bad = {"schema_version": "1.0", "event": "user_registered"}  # missing required fields
    with patch("handler.increment_error") as mock_err:
        with pytest.raises(ValidationError):
            process_message(bad, mock_db)
    mock_err.assert_called_once_with("user_registered", "validation")


def test_process_message_db_failure_raises_and_increments_error(mock_db):
    with patch.object(mock_db, "insert_event", side_effect=Exception("mongo down")), \
         patch("handler.increment_error") as mock_err:
        with pytest.raises(Exception, match="mongo down"):
            process_message(RAW_REGISTERED, mock_db)
    mock_err.assert_called_once_with("user_registered", "db")

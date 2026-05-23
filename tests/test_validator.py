import pytest
from pydantic import ValidationError
from validator import parse_event


def test_parse_user_registered():
    raw = {
        "schema_version": "1.0",
        "event": "user_registered",
        "user_id": "abc-123",
        "phone": "+1234567890",
        "entity_type": "user",
    }
    result = parse_event(raw)
    assert result.event == "user_registered"
    assert result.user_id == "abc-123"
    assert result.entity_type == "user"


def test_parse_otp_verified():
    raw = {
        "schema_version": "1.0",
        "event": "otp_verified",
        "user_id": "abc-123",
        "phone": "+1234567890",
    }
    result = parse_event(raw)
    assert result.event == "otp_verified"
    assert result.phone == "+1234567890"


def test_parse_profile_updated():
    raw = {
        "schema_version": "1.0",
        "event": "profile_updated",
        "user_id": "abc-123",
        "profile_id": "prof-456",
        "entity_type": "store",
        "name": "My Store",
        "email": "store@example.com",
        "location": "NYC",
    }
    result = parse_event(raw)
    assert result.event == "profile_updated"
    assert result.name == "My Store"


def test_parse_password_changed():
    raw = {
        "schema_version": "1.0",
        "event": "password_changed",
        "user_id": "abc-123",
        "phone": "+1234567890",
    }
    result = parse_event(raw)
    assert result.event == "password_changed"


def test_unknown_schema_version_raises():
    with pytest.raises(ValueError, match="schema_version"):
        parse_event({"schema_version": "9.9", "event": "user_registered"})


def test_unknown_event_type_raises():
    with pytest.raises(ValueError, match="event type"):
        parse_event({"schema_version": "1.0", "event": "user_deleted"})


def test_missing_required_field_raises():
    with pytest.raises(ValidationError):
        parse_event({
            "schema_version": "1.0",
            "event": "user_registered",
            # missing user_id, phone, entity_type
        })

import json
from unittest.mock import MagicMock, patch

import pytest

from user_event import UserEvent

RAW = {
    "schema_version": "1.0",
    "event": "user_registered",
    "user_id": "uid-1",
    "phone": "+1",
    "entity_type": "user",
}


@pytest.fixture
def channel():
    return MagicMock()


@pytest.fixture
def method():
    m = MagicMock()
    m.delivery_tag = 1
    m.redelivered = False
    return m


def test_valid_message_is_acked(channel, method):
    with patch("user_event.DB"):
        UserEvent.save_user_event(channel, method, MagicMock(), json.dumps(RAW).encode())
    channel.basic_ack.assert_called_once_with(delivery_tag=1)
    channel.basic_nack.assert_not_called()


def test_valid_message_inserts_to_db(channel, method):
    with patch("user_event.DB") as MockDB:
        UserEvent.save_user_event(channel, method, MagicMock(), json.dumps(RAW).encode())
    MockDB.return_value.insert_event.assert_called_once_with("user_registered", "uid-1", RAW)


def test_invalid_json_nacked_to_dlq(channel, method):
    UserEvent.save_user_event(channel, method, MagicMock(), b"not-json")
    channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)
    channel.basic_ack.assert_not_called()


def test_validation_error_nacked_to_dlq(channel, method):
    bad = json.dumps({"schema_version": "1.0", "event": "user_registered"}).encode()
    UserEvent.save_user_event(channel, method, MagicMock(), bad)
    channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)
    channel.basic_ack.assert_not_called()


def test_unknown_schema_nacked_to_dlq(channel, method):
    bad = json.dumps({"schema_version": "9.9", "event": "user_registered"}).encode()
    UserEvent.save_user_event(channel, method, MagicMock(), bad)
    channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)


def test_first_db_failure_requeues(channel, method):
    method.redelivered = False
    with patch("user_event.DB") as MockDB:
        MockDB.return_value.insert_event.side_effect = Exception("mongo down")
        UserEvent.save_user_event(channel, method, MagicMock(), json.dumps(RAW).encode())
    channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=True)


def test_redelivered_db_failure_routes_to_dlq(channel, method):
    method.redelivered = True
    with patch("user_event.DB") as MockDB:
        MockDB.return_value.insert_event.side_effect = Exception("still down")
        UserEvent.save_user_event(channel, method, MagicMock(), json.dumps(RAW).encode())
    channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)

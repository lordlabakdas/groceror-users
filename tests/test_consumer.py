import json
from unittest.mock import MagicMock, patch
import pytest

from consumer import _on_message, _declare_topology


@pytest.fixture
def channel():
    return MagicMock()


@pytest.fixture
def method():
    m = MagicMock()
    m.delivery_tag = 1
    m.redelivered = False
    return m


@pytest.fixture
def mock_db():
    return MagicMock()


RAW = {
    "schema_version": "1.0",
    "event": "user_registered",
    "user_id": "uid-1",
    "phone": "+1",
    "entity_type": "user",
}


def test_valid_message_is_acked(channel, method, mock_db):
    with patch("consumer.process_message"):
        _on_message(channel, method, MagicMock(), json.dumps(RAW).encode(), mock_db)
    channel.basic_ack.assert_called_once_with(delivery_tag=1)
    channel.basic_nack.assert_not_called()


def test_invalid_json_is_nacked_to_dlq(channel, method, mock_db):
    _on_message(channel, method, MagicMock(), b"not-json", mock_db)
    channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)
    channel.basic_ack.assert_not_called()


def test_first_failure_requeues(channel, method, mock_db):
    method.redelivered = False
    with patch("consumer.process_message", side_effect=Exception("boom")):
        _on_message(channel, method, MagicMock(), json.dumps(RAW).encode(), mock_db)
    channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=True)


def test_redelivered_failure_routes_to_dlq(channel, method, mock_db):
    method.redelivered = True
    with patch("consumer.process_message", side_effect=Exception("still failing")):
        _on_message(channel, method, MagicMock(), json.dumps(RAW).encode(), mock_db)
    channel.basic_nack.assert_called_once_with(delivery_tag=1, requeue=False)


def test_declare_topology_creates_user_queue(channel):
    _declare_topology(channel)
    queue_names = [c.args[0] if c.args else c.kwargs.get("queue") for c in channel.queue_declare.call_args_list]
    assert "user_events_queue" in queue_names
    assert "user_events_queue.dlq" in queue_names

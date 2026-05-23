import base64
import json
from unittest.mock import patch, MagicMock

import lambda_handler as lh


RAW = {
    "schema_version": "1.0",
    "event": "user_registered",
    "user_id": "uid-1",
    "phone": "+1",
    "entity_type": "user",
}


def _amq_event(raw: dict) -> dict:
    encoded = base64.b64encode(json.dumps(raw).encode()).decode()
    return {
        "rmqMessagesByQueue": {
            "user_events_queue::/": [{"data": encoded, "redelivered": False}]
        }
    }


def _sqs_event(raw: dict) -> dict:
    return {"Records": [{"body": json.dumps(raw), "messageId": "msg-1"}]}


def test_amazon_mq_event_calls_process_message():
    with patch("lambda_handler._get_db", return_value=MagicMock()), \
         patch("lambda_handler.process_message") as mock_proc:
        result = lh.handler(_amq_event(RAW), None)
    mock_proc.assert_called_once()
    assert result["failed"] == 0


def test_sqs_event_calls_process_message():
    with patch("lambda_handler._get_db", return_value=MagicMock()), \
         patch("lambda_handler.process_message") as mock_proc:
        result = lh.handler(_sqs_event(RAW), None)
    mock_proc.assert_called_once()
    assert result["failed"] == 0


def test_process_failure_increments_failed_count():
    with patch("lambda_handler._get_db", return_value=MagicMock()), \
         patch("lambda_handler.process_message", side_effect=Exception("boom")):
        result = lh.handler(_sqs_event(RAW), None)
    assert result["failed"] == 1

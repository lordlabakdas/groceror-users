import pytest
from unittest.mock import patch, MagicMock
import metrics as metrics_module


def test_increment_event_calls_counter():
    with patch.object(metrics_module.events_total, "labels") as mock_labels:
        mock_labels.return_value = MagicMock()
        metrics_module.increment_event("user_registered")
        mock_labels.assert_called_once_with(event_type="user_registered")
        mock_labels.return_value.inc.assert_called_once()


def test_increment_error_calls_counter():
    with patch.object(metrics_module.processing_errors_total, "labels") as mock_labels:
        mock_labels.return_value = MagicMock()
        metrics_module.increment_error("user_registered", "validation")
        mock_labels.assert_called_once_with(event_type="user_registered", reason="validation")
        mock_labels.return_value.inc.assert_called_once()


def test_set_consumer_status_up():
    with patch.object(metrics_module.consumer_up, "set") as mock_set:
        metrics_module.set_consumer_status(True)
        mock_set.assert_called_once_with(1)


def test_set_consumer_status_down():
    with patch.object(metrics_module.consumer_up, "set") as mock_set:
        metrics_module.set_consumer_status(False)
        mock_set.assert_called_once_with(0)


def test_pushgateway_push_called_when_backend_is_pushgateway():
    with patch.object(metrics_module, "_push_if_needed") as mock_push:
        metrics_module.increment_event("otp_verified")
        mock_push.assert_called_once()


def test_pushgateway_failure_does_not_raise():
    with patch("metrics.config") as mock_config, \
         patch("metrics.push_to_gateway", side_effect=Exception("network error")):
        mock_config.METRICS_BACKEND = "pushgateway"
        mock_config.PUSHGATEWAY_URL = "http://nowhere"
        # Should not raise
        metrics_module._push_if_needed()

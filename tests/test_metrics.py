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


def test_set_consumer_up_1():
    with patch.object(metrics_module.consumer_up, "set") as mock_set:
        metrics_module.set_consumer_up(1)
        mock_set.assert_called_once_with(1)


def test_set_consumer_up_0():
    with patch.object(metrics_module.consumer_up, "set") as mock_set:
        metrics_module.set_consumer_up(0)
        mock_set.assert_called_once_with(0)


def test_pushgateway_push_called_when_backend_is_pushgateway():
    with patch("metrics.push_to_gateway") as mock_push, \
         patch("metrics.config") as mock_config:
        mock_config.METRICS_BACKEND = "pushgateway"
        mock_config.PUSHGATEWAY_URL = "http://localhost:9091"
        metrics_module._push_if_needed()
        mock_push.assert_called_once()


def test_pushgateway_not_called_for_prometheus_backend():
    with patch("metrics.push_to_gateway") as mock_push, \
         patch("metrics.config") as mock_config:
        mock_config.METRICS_BACKEND = "prometheus"
        metrics_module._push_if_needed()
        mock_push.assert_not_called()


def test_pushgateway_failure_does_not_raise():
    with patch("metrics.config") as mock_config, \
         patch("metrics.push_to_gateway", side_effect=Exception("network error")):
        mock_config.METRICS_BACKEND = "pushgateway"
        mock_config.PUSHGATEWAY_URL = "http://nowhere"
        # Should not raise
        metrics_module._push_if_needed()

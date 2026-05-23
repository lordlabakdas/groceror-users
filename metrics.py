import logging

from prometheus_client import Counter, Gauge, push_to_gateway, REGISTRY

import config

log = logging.getLogger(__name__)

events_total = Counter(
    "groceror_users_events_total",
    "Total user events successfully processed",
    ["event_type"],
)
processing_errors_total = Counter(
    "groceror_users_processing_errors_total",
    "Total user event processing errors",
    ["event_type", "reason"],
)
consumer_up = Gauge(
    "groceror_users_consumer_up",
    "1 when pika consumer is connected, 0 otherwise",
)


def increment_event(event_type: str) -> None:
    events_total.labels(event_type=event_type).inc()
    _push_if_needed()


def increment_error(event_type: str, reason: str) -> None:
    processing_errors_total.labels(event_type=event_type, reason=reason).inc()
    _push_if_needed()


def set_consumer_status(up: bool) -> None:
    consumer_up.set(1 if up else 0)
    _push_if_needed()


def _push_if_needed() -> None:
    if config.METRICS_BACKEND == "pushgateway":
        try:
            push_to_gateway(config.PUSHGATEWAY_URL, job="groceror-users", registry=REGISTRY)
        except Exception as exc:
            log.warning("Pushgateway push failed: %s", exc)

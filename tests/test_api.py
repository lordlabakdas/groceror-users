import pytest
from fastapi.testclient import TestClient
from api import app

client = TestClient(app)


def test_health_returns_ok():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_metrics_returns_prometheus_text():
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "groceror_users_events_total" in resp.text
    assert resp.headers["content-type"].startswith("text/plain")

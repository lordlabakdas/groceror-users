import logging

import metrics  # noqa: F401 - imported to register prometheus metrics
from fastapi import FastAPI, HTTPException, Query
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

from analytics.user_analytics import UserAnalytics
from analytics.user_per_day_analytics import UserPerDayAnalytics
from db import DB

logger = logging.getLogger(__name__)

app = FastAPI(title="groceror-users analytics", version="1.0")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def get_metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


def _analytics():
    db = DB()
    return db, UserAnalytics(db), UserPerDayAnalytics(db)


@app.get("/analytics/registrations-per-day")
def registrations_per_day(limit: int = Query(default=30, ge=1, le=365)):
    db, _, per_day = _analytics()
    try:
        return {"days": per_day.registrations_per_day(limit)}
    except Exception as exc:
        logger.error("registrations_per_day failed: %s", exc)
        raise HTTPException(status_code=500, detail="Analytics query failed")
    finally:
        db.close()


@app.get("/analytics/events-per-day")
def events_per_day(limit: int = Query(default=30, ge=1, le=365)):
    db, _, per_day = _analytics()
    try:
        return {"days": per_day.events_per_day(limit)}
    except Exception as exc:
        logger.error("events_per_day failed: %s", exc)
        raise HTTPException(status_code=500, detail="Analytics query failed")
    finally:
        db.close()


@app.get("/analytics/summary")
def summary():
    db, analytics, _ = _analytics()
    try:
        return {
            "total_users": analytics.total_users(),
            "active_users": analytics.active_users(),
            "users_by_entity_type": analytics.users_by_entity_type(),
            "event_counts": analytics.event_counts(),
        }
    except Exception as exc:
        logger.error("summary failed: %s", exc)
        raise HTTPException(status_code=500, detail="Analytics query failed")
    finally:
        db.close()

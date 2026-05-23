# /code/groceror-users/config.py
import os

RABBITMQ_HOST  = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT  = int(os.getenv("RABBITMQ_PORT", 5672))
RABBITMQ_USER  = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS  = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_VHOST = os.getenv("RABBITMQ_VHOST", "/")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")

API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8002))

METRICS_BACKEND  = os.getenv("METRICS_BACKEND", "prometheus")
PUSHGATEWAY_URL  = os.getenv("PUSHGATEWAY_URL", "http://localhost:9091")

QUEUE_NAME   = "user_events_queue"
DLQ_NAME     = "user_events_queue.dlq"
DLX_EXCHANGE = "dlx"

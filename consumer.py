import json
import logging
import time

import pika

import config
from db import DB
from handler import process_message
from metrics import set_consumer_status

log = logging.getLogger(__name__)


def _setup_connection() -> pika.BlockingConnection:
    credentials = pika.PlainCredentials(config.RABBITMQ_USER, config.RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=config.RABBITMQ_HOST,
        port=config.RABBITMQ_PORT,
        virtual_host=config.RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300,
    )
    return pika.BlockingConnection(params)


def _declare_topology(channel) -> None:
    channel.exchange_declare(exchange=config.DLX_EXCHANGE, exchange_type="direct", durable=True)
    channel.queue_declare(queue=config.DLQ_NAME, durable=True)
    channel.queue_bind(
        exchange=config.DLX_EXCHANGE,
        queue=config.DLQ_NAME,
        routing_key=config.QUEUE_NAME,
    )
    channel.queue_declare(
        queue=config.QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": config.DLX_EXCHANGE,
            "x-dead-letter-routing-key": config.QUEUE_NAME,
        },
    )


def _on_message(channel, method, properties, body: bytes, db: DB) -> None:
    try:
        raw = json.loads(body)
    except json.JSONDecodeError:
        log.error("Invalid JSON body, routing to DLQ")
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        return

    try:
        process_message(raw, db)
        channel.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as exc:
        if method.redelivered:
            log.error("Redelivered message still failing, routing to DLQ: %s", exc)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        else:
            log.warning("Processing failed, requeueing once: %s", exc)
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


def start(db: DB) -> None:
    """Blocking consumer loop with reconnect-on-failure. Runs forever."""
    while True:
        connection = None
        try:
            connection = _setup_connection()
            channel = connection.channel()
            _declare_topology(channel)
            channel.basic_qos(prefetch_count=1)
            set_consumer_status(True)
            log.info("groceror-users consumer started, waiting for messages...")
            channel.basic_consume(
                queue=config.QUEUE_NAME,
                on_message_callback=lambda ch, m, p, b: _on_message(ch, m, p, b, db),
            )
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            set_consumer_status(False)
            log.error("Lost RabbitMQ connection. Retrying in 5s...")
        except Exception as exc:
            set_consumer_status(False)
            log.error("Unexpected error: %s. Retrying in 5s...", exc)
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass
            time.sleep(5)

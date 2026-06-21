import logging
import threading
import time

import pika
import uvicorn

import config
import metrics
from user_event import UserEvent

logger = logging.getLogger(__name__)


def setup_rabbit_connection():
    credentials = pika.PlainCredentials(config.RABBITMQ_USER, config.RABBITMQ_PASS)
    parameters = pika.ConnectionParameters(
        host=config.RABBITMQ_HOST,
        port=config.RABBITMQ_PORT,
        virtual_host=config.RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300,
    )
    return pika.BlockingConnection(parameters)


def _declare_topology(channel):
    channel.exchange_declare(exchange=config.DLX_EXCHANGE, exchange_type="direct", durable=True)
    channel.queue_declare(queue=config.DLQ_NAME, durable=True)
    channel.queue_bind(exchange=config.DLX_EXCHANGE, queue=config.DLQ_NAME, routing_key=config.QUEUE_NAME)
    channel.queue_declare(
        queue=config.QUEUE_NAME,
        durable=True,
        arguments={
            "x-dead-letter-exchange": config.DLX_EXCHANGE,
            "x-dead-letter-routing-key": config.QUEUE_NAME,
        },
    )


def start_consumer():
    while True:
        try:
            connection = setup_rabbit_connection()
            channel = connection.channel()
            _declare_topology(channel)
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(
                queue=config.QUEUE_NAME, on_message_callback=UserEvent.save_user_event
            )
            logger.info("groceror-users consumer started. Waiting for messages...")
            metrics.set_consumer_up(1)
            channel.start_consuming()
        except pika.exceptions.AMQPConnectionError:
            logger.error("Lost connection to RabbitMQ. Retrying in 5 seconds...")
            metrics.set_consumer_up(0)
            time.sleep(5)
        except Exception as exc:
            logger.error("Unexpected error: %s. Retrying in 5 seconds...", exc)
            metrics.set_consumer_up(0)
            time.sleep(5)


def start_api():
    uvicorn.run(
        "api:app",
        host=config.API_HOST,
        port=config.API_PORT,
        log_level="info",
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()

    start_api()

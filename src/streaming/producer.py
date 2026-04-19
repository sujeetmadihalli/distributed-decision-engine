"""Kafka/Redpanda producer — publishes telemetry events to the streaming topic."""

from confluent_kafka import Producer
import json
import os
import logging

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:19092")
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "telemetry.raw")
TOPIC_DECISIONS = os.getenv("KAFKA_TOPIC_DECISIONS", "telemetry.decisions")


def _delivery_report(err, msg):
    if err:
        logger.error("Delivery failed: %s", err)
    else:
        logger.debug("Delivered to %s [%d] @ %d", msg.topic(), msg.partition(), msg.offset())


class EventProducer:
    def __init__(self, bootstrap_servers: str = KAFKA_BOOTSTRAP):
        self.producer = Producer({
            "bootstrap.servers": bootstrap_servers,
            "client.id": "decision-engine-producer",
            "acks": "all",
            "retries": 3,
        })

    def send_event(self, event: dict, topic: str = TOPIC_RAW):
        self.producer.produce(
            topic=topic,
            key=event.get("event_id", "").encode(),
            value=json.dumps(event).encode(),
            callback=_delivery_report,
        )
        self.producer.poll(0)

    def send_decision(self, decision: dict):
        self.producer.produce(
            topic=TOPIC_DECISIONS,
            key=decision.get("event_id", "").encode(),
            value=json.dumps(decision).encode(),
            callback=_delivery_report,
        )
        self.producer.poll(0)

    def flush(self):
        self.producer.flush()

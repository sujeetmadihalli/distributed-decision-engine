"""Kafka/Redpanda consumer — reads raw telemetry, runs the decision pipeline, publishes results."""

from confluent_kafka import Consumer, KafkaError
import json
import os
import logging
import signal
import sys

from src.vector_db.memory import MemoryLayer
from src.llm.orchestrator import Orchestrator
from src.streaming.producer import EventProducer

logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP", "localhost:19092")
TOPIC_RAW = os.getenv("KAFKA_TOPIC_RAW", "telemetry.raw")
CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "decision-engine-group")


class EventConsumer:
    def __init__(self):
        self.consumer = Consumer({
            "bootstrap.servers": KAFKA_BOOTSTRAP,
            "group.id": CONSUMER_GROUP,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        })
        self.memory = MemoryLayer()
        self.brain = Orchestrator()
        self.producer = EventProducer()
        self._running = True

    def _process_event(self, event: dict) -> dict:
        payload_str = str(event.get("payload", {}))

        self.memory.store_event(
            text=payload_str,
            metadata={"event_id": event["event_id"], "source": event.get("source", "unknown")},
        )

        context = self.memory.search_similar(payload_str, limit=3)
        decision = self.brain.route_event(event, context)

        return {
            "event_id": event["event_id"],
            "source": event.get("source"),
            "decision": decision,
            "historical_matches": len(context),
        }

    def run(self):
        self.consumer.subscribe([TOPIC_RAW])
        logger.info("Consumer started — listening on %s", TOPIC_RAW)

        def _shutdown(sig, frame):
            logger.info("Shutting down consumer...")
            self._running = False

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        try:
            while self._running:
                msg = self.consumer.poll(timeout=1.0)
                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error("Consumer error: %s", msg.error())
                    continue

                try:
                    event = json.loads(msg.value().decode())
                    logger.info("Processing event %s from %s", event.get("event_id"), event.get("source"))
                    result = self._process_event(event)
                    self.producer.send_decision(result)
                    self.consumer.commit(asynchronous=False)
                    logger.info("Decision for %s: %s", event.get("event_id"), result["decision"])
                except json.JSONDecodeError:
                    logger.error("Invalid JSON in message: %s", msg.value())
                except Exception:
                    logger.exception("Failed to process event")
        finally:
            self.consumer.close()
            self.producer.flush()
            logger.info("Consumer shut down cleanly")


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    consumer = EventConsumer()
    consumer.run()


if __name__ == "__main__":
    main()

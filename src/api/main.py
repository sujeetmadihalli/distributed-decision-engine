from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import logging
import os
import time

from src.vector_db.memory import MemoryLayer
from src.llm.orchestrator import Orchestrator
from src.streaming.flink_processor import FlinkProcessor
from src.rl.inference import RLAdvisor
from src.api.metrics import (
    EVENTS_INGESTED, DECISIONS_MADE, INGEST_LATENCY,
    VECTOR_SEARCH_LATENCY, LLM_LATENCY, ACTIVE_WINDOWS,
    BURST_DETECTIONS, RL_RECOMMENDATIONS, metrics_endpoint,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

ENABLE_KAFKA = os.getenv("ENABLE_KAFKA", "false").lower() == "true"

app = FastAPI(title="Decision Engine API", version="1.0.0")

memory = MemoryLayer()
brain = Orchestrator()
flink = FlinkProcessor(window_seconds=60, burst_threshold=10)
rl_advisor = RLAdvisor()

producer = None
if ENABLE_KAFKA:
    from src.streaming.producer import EventProducer
    producer = EventProducer()
    logger.info("Kafka producer enabled")


class TelemetryEvent(BaseModel):
    event_id: str
    source: str
    timestamp: float
    payload: Dict[str, Any]


@app.post("/ingest")
async def ingest_telemetry(event: TelemetryEvent):
    start = time.monotonic()
    try:
        event_dict = event.model_dump()
        EVENTS_INGESTED.labels(source=event.source).inc()

        enriched = flink.process(event_dict)
        if enriched.get("enrichment", {}).get("is_burst"):
            BURST_DETECTIONS.labels(source=event.source).inc()

        ACTIVE_WINDOWS.set(len([w for w in flink.get_window_stats().values() if w["is_active"]]))

        if producer:
            producer.send_event(event_dict)

        t0 = time.monotonic()
        memory.store_event(
            text=str(event.payload),
            metadata={"event_id": event.event_id, "source": event.source},
        )
        context = memory.search_similar(str(event.payload), limit=3)
        VECTOR_SEARCH_LATENCY.observe(time.monotonic() - t0)

        t1 = time.monotonic()
        decision = brain.route_event(enriched, context)
        LLM_LATENCY.observe(time.monotonic() - t1)

        action = decision.get("decision", {}).get("action", "unknown")
        DECISIONS_MADE.labels(action=action).inc()

        rl_recommendation = rl_advisor.recommend({
            "severity": enriched.get("enrichment", {}).get("events_per_second", 0.3),
            "event_rate": enriched.get("enrichment", {}).get("events_per_second", 0.3),
            "is_burst": enriched.get("enrichment", {}).get("is_burst", False),
            "historical_matches": len(context),
            "llm_confidence": decision.get("decision", {}).get("confidence", 0.5),
            "payload_complexity": len(event.payload) / 20.0,
            "source_frequency": enriched.get("enrichment", {}).get("window_event_count", 1) / 100.0,
            "time_since_last": 0.5,
        })

        if rl_recommendation:
            RL_RECOMMENDATIONS.labels(action=rl_recommendation["rl_action"]).inc()

        INGEST_LATENCY.observe(time.monotonic() - start)

        return {
            "status": "processed",
            "event_id": event.event_id,
            "decision": decision,
            "rl_recommendation": rl_recommendation,
            "enrichment": enriched.get("enrichment"),
            "historical_matches": len(context),
        }
    except Exception as e:
        logger.exception("Ingestion failed for event %s", event.event_id)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Decision Engine v1.0",
        "kafka": ENABLE_KAFKA,
        "rl_enabled": rl_advisor.enabled,
    }


@app.get("/windows")
async def get_window_stats():
    return flink.get_window_stats()


app.get("/metrics")(metrics_endpoint)

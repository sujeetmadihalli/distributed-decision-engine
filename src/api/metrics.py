"""Prometheus metrics for the Decision Engine API."""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response

EVENTS_INGESTED = Counter(
    "decision_engine_events_ingested_total",
    "Total telemetry events ingested",
    ["source"],
)

DECISIONS_MADE = Counter(
    "decision_engine_decisions_total",
    "Total routing decisions made",
    ["action"],
)

INGEST_LATENCY = Histogram(
    "decision_engine_ingest_seconds",
    "Ingestion pipeline latency in seconds",
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

VECTOR_SEARCH_LATENCY = Histogram(
    "decision_engine_vector_search_seconds",
    "Vector similarity search latency",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25],
)

LLM_LATENCY = Histogram(
    "decision_engine_llm_seconds",
    "LLM routing decision latency",
    buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ACTIVE_WINDOWS = Gauge(
    "decision_engine_active_windows",
    "Number of active Flink processor windows",
)

BURST_DETECTIONS = Counter(
    "decision_engine_burst_detections_total",
    "Total burst pattern detections",
    ["source"],
)

RL_RECOMMENDATIONS = Counter(
    "decision_engine_rl_recommendations_total",
    "RL advisor recommendations made",
    ["action"],
)


async def metrics_endpoint():
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

"""
Stateful Flink-style stream processor.

Implements windowed aggregation, anomaly detection, and event enrichment
that runs between raw ingestion and the decision pipeline.

In production, this would be a PyFlink job. Here we implement the core
processing logic that can be wrapped in either PyFlink or the Kafka consumer.
"""

import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class WindowState:
    event_count: int = 0
    sources: dict = field(default_factory=lambda: defaultdict(int))
    payload_keys: dict = field(default_factory=lambda: defaultdict(int))
    first_seen: float = 0.0
    last_seen: float = 0.0


class FlinkProcessor:
    """
    Stateful stream processor that:
    1. Maintains tumbling windows per source (configurable duration)
    2. Detects burst patterns (>N events in window)
    3. Enriches events with window-level aggregates
    4. Emits alerts for anomalous patterns
    """

    def __init__(self, window_seconds: int = 60, burst_threshold: int = 10):
        self.window_seconds = window_seconds
        self.burst_threshold = burst_threshold
        self.windows: dict[str, WindowState] = {}

    def _get_window(self, source: str, timestamp: float) -> WindowState:
        if source not in self.windows:
            self.windows[source] = WindowState(first_seen=timestamp)

        window = self.windows[source]
        if timestamp - window.first_seen > self.window_seconds:
            self.windows[source] = WindowState(first_seen=timestamp)
            window = self.windows[source]

        return window

    def process(self, event: dict) -> dict:
        source = event.get("source", "unknown")
        timestamp = event.get("timestamp", time.time())
        payload = event.get("payload", {})

        window = self._get_window(source, timestamp)
        window.event_count += 1
        window.last_seen = timestamp
        window.sources[source] += 1

        for key in payload:
            window.payload_keys[key] += 1

        is_burst = window.event_count >= self.burst_threshold
        window_duration = window.last_seen - window.first_seen
        events_per_second = window.event_count / max(window_duration, 0.001)

        enriched = {
            **event,
            "enrichment": {
                "window_event_count": window.event_count,
                "window_duration_s": round(window_duration, 2),
                "events_per_second": round(events_per_second, 2),
                "is_burst": is_burst,
                "dominant_payload_keys": sorted(
                    window.payload_keys.items(), key=lambda x: -x[1]
                )[:5],
            },
        }

        if is_burst:
            logger.warning(
                "BURST detected from %s: %d events in %.1fs (%.1f/s)",
                source, window.event_count, window_duration, events_per_second,
            )

        return enriched

    def get_window_stats(self) -> dict:
        now = time.time()
        return {
            source: {
                "event_count": w.event_count,
                "age_seconds": round(now - w.first_seen, 1),
                "is_active": (now - w.last_seen) < self.window_seconds,
            }
            for source, w in self.windows.items()
        }

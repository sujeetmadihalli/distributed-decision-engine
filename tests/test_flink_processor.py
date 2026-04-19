import time
from src.streaming.flink_processor import FlinkProcessor


def test_basic_processing():
    fp = FlinkProcessor(window_seconds=60, burst_threshold=5)
    event = {"event_id": "e1", "source": "sensor_a", "timestamp": time.time(), "payload": {"temp": 95}}
    result = fp.process(event)
    assert "enrichment" in result
    assert result["enrichment"]["window_event_count"] == 1
    assert result["enrichment"]["is_burst"] is False


def test_burst_detection():
    fp = FlinkProcessor(window_seconds=60, burst_threshold=3)
    base_time = time.time()
    for i in range(5):
        result = fp.process({
            "event_id": f"e{i}", "source": "sensor_a",
            "timestamp": base_time + i * 0.1,
            "payload": {"value": i},
        })

    assert result["enrichment"]["is_burst"] is True
    assert result["enrichment"]["window_event_count"] == 5


def test_window_expiry():
    fp = FlinkProcessor(window_seconds=1, burst_threshold=100)
    t = time.time()
    fp.process({"event_id": "e1", "source": "s1", "timestamp": t, "payload": {}})
    result = fp.process({"event_id": "e2", "source": "s1", "timestamp": t + 2, "payload": {}})
    assert result["enrichment"]["window_event_count"] == 1


def test_multiple_sources():
    fp = FlinkProcessor(window_seconds=60, burst_threshold=10)
    t = time.time()
    fp.process({"event_id": "e1", "source": "sensor_a", "timestamp": t, "payload": {}})
    fp.process({"event_id": "e2", "source": "sensor_b", "timestamp": t, "payload": {}})
    fp.process({"event_id": "e3", "source": "sensor_a", "timestamp": t + 1, "payload": {}})

    stats = fp.get_window_stats()
    assert stats["sensor_a"]["event_count"] == 2
    assert stats["sensor_b"]["event_count"] == 1


def test_payload_key_tracking():
    fp = FlinkProcessor(window_seconds=60, burst_threshold=10)
    t = time.time()
    fp.process({"event_id": "e1", "source": "s1", "timestamp": t, "payload": {"temp": 1, "cpu": 0.5}})
    result = fp.process({"event_id": "e2", "source": "s1", "timestamp": t + 1, "payload": {"temp": 2, "mem": 0.8}})
    keys = dict(result["enrichment"]["dominant_payload_keys"])
    assert keys["temp"] == 2

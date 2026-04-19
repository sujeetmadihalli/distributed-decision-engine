import os
os.environ["USE_MOCK_LLM"] = "true"

from src.llm.orchestrator import Orchestrator


def test_mock_routing():
    brain = Orchestrator()
    result = brain.route_event(
        event_data={"event_id": "t1", "source": "sensor", "payload": {"temp": 100}},
        historical_context=[{"text": "past event", "event_id": "old"}],
    )
    assert "decision" in result
    assert result["decision"]["action"] == "escalate_to_maintenance"
    assert result["decision"]["confidence"] == 0.92


def test_routing_empty_context():
    brain = Orchestrator()
    result = brain.route_event(
        event_data={"event_id": "t2", "source": "sensor", "payload": {}},
        historical_context=[],
    )
    assert "decision" in result
    assert "action" in result["decision"]

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List

from src.vector_db.memory import MemoryLayer
from src.llm.orchestrator import Orchestrator

app = FastAPI(title="Decision Engine API", version="0.1.0")

# Initialize core components
memory = MemoryLayer()
brain = Orchestrator()

class TelemetryEvent(BaseModel):
    event_id: str
    source: str
    timestamp: float
    payload: Dict[str, Any]

@app.post("/ingest")
async def ingest_telemetry(event: TelemetryEvent):
    """
    Simulated ingestion endpoint for Phase 1.
    In Phase 2, this will be replaced/complemented by Flink streaming.
    """
    event_dict = event.dict()
    
    # 1. Store event in Memory Layer
    memory.store_event(
        text=str(event.payload),
        metadata={"event_id": event.event_id, "source": event.source}
    )
    
    # 2. Retrieve historical context for similar events
    context = memory.search_similar(str(event.payload), limit=3)
    
    # 3. Route event to AI Brain for decision
    decision = brain.route_event(event_dict, context)
    
    return {
        "status": "processed",
        "event_id": event.event_id,
        "decision": decision,
        "historical_matches": len(context)
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Decision Engine Core API"}

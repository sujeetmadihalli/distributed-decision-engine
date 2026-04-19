import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_health():
    from src.api.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_ingest():
    from src.api.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/ingest", json={
            "event_id": "test-001",
            "source": "pressure_sensor",
            "timestamp": 1234567890.0,
            "payload": {"pressure": "high", "alert": True},
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "processed"
        assert data["event_id"] == "test-001"
        assert "decision" in data
        assert "enrichment" in data
        assert "historical_matches" in data


@pytest.mark.asyncio
async def test_ingest_invalid_payload():
    from src.api.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/ingest", json={"event_id": "bad"})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_windows_endpoint():
    from src.api.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/windows")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)


@pytest.mark.asyncio
async def test_ingest_builds_history():
    from src.api.main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/ingest", json={
            "event_id": "hist-001", "source": "temp_sensor",
            "timestamp": 1000.0, "payload": {"temp": "high"},
        })
        resp = await client.post("/ingest", json={
            "event_id": "hist-002", "source": "temp_sensor",
            "timestamp": 1001.0, "payload": {"temp": "high"},
        })
        data = resp.json()
        assert data["historical_matches"] >= 1

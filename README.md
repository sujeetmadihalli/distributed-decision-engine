# Distributed Multi-Agent Decision Engine

A production-grade system for real-time telemetry event processing, LLM-driven semantic routing, reinforcement learning optimization, and cloud-native deployment.

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌────────────────┐     ┌─────────────┐
│  Telemetry   │────▶│ Redpanda │────▶│ Flink Processor│────▶│   Qdrant    │
│  Sources     │     │ (Kafka)  │     │ (Windowing +   │     │ (Vector DB) │
└─────────────┘     └──────────┘     │  Enrichment)   │     └──────┬──────┘
                                     └───────┬────────┘            │
                                             │              Similar Events
                                             ▼                     │
                                     ┌───────────────┐            │
                                     │  LLM Router   │◀───────────┘
                                     │  (LangChain)  │
                                     └───────┬───────┘
                                             │
                                     ┌───────▼───────┐
                                     │  RL Optimizer  │
                                     │  (Ray RLlib)   │
                                     └───────┬───────┘
                                             │
                                     ┌───────▼───────┐
                                     │   Decision     │
                                     │   Output       │
                                     └───────────────┘
```

## Project Phases

- [x] **Phase 1: Local Prototype** — FastAPI + Qdrant (real embeddings) + LangChain orchestrator
- [x] **Phase 2: Streaming** — Redpanda (Kafka-compatible) + Flink-style stateful processor with windowed aggregation and burst detection
- [x] **Phase 3: RL Optimizer** — Gymnasium environment + Ray RLlib PPO agent that learns optimal routing from reward signals
- [x] **Phase 4: Cloud Infrastructure** — Dockerfile, Terraform (GCP/GKE), K8s manifests, ArgoCD GitOps, Prometheus/Grafana observability

## Technology Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Uvicorn |
| Streaming | Redpanda (Kafka) + Flink-style processor |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2) |
| Vector DB | Qdrant (COSINE similarity, 384-dim) |
| LLM Routing | LangChain + OpenAI (with mock fallback) |
| RL Optimization | Ray RLlib (PPO) + Gymnasium |
| Observability | Prometheus + Grafana |
| Infrastructure | Terraform (GCP) + GKE + ArgoCD |
| Containerization | Docker |

## Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose

### 1. Start infrastructure
```bash
docker compose up -d  # Qdrant + Redpanda + Redpanda Console
```

### 2. Install dependencies
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the API
```bash
# Mock mode (no OpenAI key needed)
USE_MOCK_LLM=true python3 run_api.py

# Real LLM mode
OPENAI_API_KEY=sk-... python3 run_api.py
```

### 4. Send a test event
```bash
curl -X POST http://localhost:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{
    "event_id": "evt-001",
    "source": "pressure_sensor",
    "timestamp": 1234567890.0,
    "payload": {"pressure": "high", "alert": true}
  }'
```

### 5. Run the streaming consumer (optional)
```bash
ENABLE_KAFKA=true python3 -m src.streaming.consumer
```

### 6. Train the RL agent (optional)
```bash
python3 -m src.rl.trainer
```

### 7. Run tests
```bash
pytest tests/ -v
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/ingest` | Ingest telemetry event → enrich → store → search similar → route decision |
| GET | `/health` | Health check with feature flags |
| GET | `/windows` | Active Flink processor window statistics |
| GET | `/metrics` | Prometheus metrics |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | `http://localhost:6333` | Qdrant connection URL |
| `EMBED_MODEL` | `all-MiniLM-L6-v2` | Sentence transformer model |
| `KAFKA_BOOTSTRAP` | `localhost:19092` | Redpanda/Kafka bootstrap servers |
| `ENABLE_KAFKA` | `false` | Enable Kafka producer in API |
| `LLM_MODEL` | `gpt-3.5-turbo` | OpenAI model for routing |
| `USE_MOCK_LLM` | `false` | Use mocked LLM responses |
| `OPENAI_API_KEY` | — | OpenAI API key (required if USE_MOCK_LLM=false) |
| `USE_RL` | `false` | Enable RL advisor recommendations |
| `RL_CHECKPOINT_DIR` | `checkpoints/rl` | Path to trained RL checkpoints |

## Project Structure

```
├── src/
│   ├── api/
│   │   ├── main.py              # FastAPI app with all endpoints
│   │   └── metrics.py           # Prometheus metric definitions
│   ├── vector_db/
│   │   └── memory.py            # Qdrant + sentence-transformers
│   ├── llm/
│   │   └── orchestrator.py      # LangChain routing with real/mock LLM
│   ├── streaming/
│   │   ├── producer.py          # Kafka event producer
│   │   ├── consumer.py          # Kafka consumer → decision pipeline
│   │   └── flink_processor.py   # Stateful windowed stream processor
│   └── rl/
│       ├── environment.py       # Gymnasium env with reward shaping
│       ├── trainer.py           # Ray RLlib PPO training
│       └── inference.py         # RL advisor for production
├── infra/
│   ├── terraform/main.tf        # GCP: VPC, GKE, Artifact Registry
│   ├── k8s/                     # Kubernetes manifests
│   ├── argocd/application.yaml  # GitOps deployment
│   └── monitoring/              # Prometheus + Grafana configs
├── tests/                       # pytest test suite
├── docker-compose.yml           # Qdrant + Redpanda + Console
├── Dockerfile                   # API container
├── Dockerfile.consumer          # Streaming consumer container
└── 01_vanilla_tool_calling.py   # Educational: LLM tool-calling demo
```

## RL Environment

The RL agent observes 8 features per event and chooses from 4 actions:

**Observation:** severity, event_rate, is_burst, historical_matches, llm_confidence, payload_complexity, source_frequency, time_since_last

**Actions:** escalate_to_maintenance, auto_resolve, scale_up, ignore

**Reward shaping:**
- Correct critical escalation: +10
- Correct auto-resolve: +7 (with efficiency bonus)
- Correct burst scale-up: +8
- Missed critical: -15
- False escalation: -5

## Cloud Deployment

```bash
# 1. Provision GCP infrastructure
cd infra/terraform
terraform init && terraform apply

# 2. Build & push containers
docker build -t $REGISTRY/decision-engine-api .
docker build -f Dockerfile.consumer -t $REGISTRY/decision-engine-consumer .
docker push $REGISTRY/decision-engine-api
docker push $REGISTRY/decision-engine-consumer

# 3. Deploy via ArgoCD
kubectl apply -f infra/argocd/application.yaml
```

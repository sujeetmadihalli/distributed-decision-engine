# Distributed Multi-Agent Decision Engine

Welcome to the Distributed Multi-Agent Decision Engine! This repository contains a Staff-engineer level system designed for real-time event streaming, LLM-driven semantic reasoning, and Reinforcement Learning-based optimization. 

## Project Execution Phases

The architecture is being built iteratively in four phases:

- [x] **Phase 1: Local Prototype (The "Brain")** - A FastAPI backend, an embedded Vector DB (Qdrant), and an LLM Orchestrator (LangChain) that can ingest synthetic events and perform semantic routing.
- [ ] **Phase 2: Streaming Integration (The Data Firehose)** - Deploying local Redpanda (Kafka) and Apache Flink to handle massive, stateful data streams.
- [ ] **Phase 3: The RL Optimizer (Advanced Decision Making)** - Incorporating Ray RLlib to train agents that mathematically optimize the semantic decisions made by the LLM.
- [ ] **Phase 4: Productionization (Cloud Infrastructure)** - Writing Terraform configs to deploy the entire stack to GCP using Kubernetes, GitOps (ArgoCD), and an observability stack.

## Architecture & Technology Stack
* **Ingestion:** Redpanda & Apache Flink
* **Serving & Microservices:** FastAPI & vLLM
* **Reasoning (AI Core):** LangChain & Qdrant (Vector DB)
* **Optimization:** Ray RLlib
* **Infrastructure:** GCP, Terraform, GKE & ArgoCD

## Phase 1 Quickstart

### Prerequisites 
- Python 3.10+

### Setup
1. Clone the repository
2. Create your virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
   
*(Note: To bypass WSL2 PyTorch compilation hangs and OpenAI API validation mismatch errors, `MockEmbeddings` and a mocked `route_event` method are currently active in the `src/vector_db/memory.py` and `src/llm/orchestrator.py` files to demonstrate the API workflow)*

### Running the API
Boot the FastAPI application:
```bash
python3 run_api.py
```

Send a test telemetry event to the `/ingest` endpoint:
```bash
curl -X POST -H 'Content-Type: application/json' -d '{"event_id": "evt-002", "source": "pressure_sensor", "timestamp": 12345679.0, "payload": {"pressure": "high", "alert": true}}' http://localhost:8000/ingest
```

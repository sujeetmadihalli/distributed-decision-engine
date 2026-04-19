import os

os.environ["USE_MOCK_LLM"] = "true"
os.environ["USE_RL"] = "false"
os.environ["QDRANT_URL"] = ":memory:"

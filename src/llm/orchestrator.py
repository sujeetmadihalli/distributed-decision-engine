from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
import os
import json
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
USE_MOCK_LLM = os.getenv("USE_MOCK_LLM", "false").lower() == "true"


class Orchestrator:
    def __init__(self):
        self.routing_prompt = PromptTemplate(
            input_variables=["event_data", "historical_context"],
            template="""You are a strategic routing agent in a distributed decision engine.

Received an event:
{event_data}

Historical context for similar events:
{historical_context}

Based on this, what immediate technical action should be taken?
Respond ONLY with a JSON object with these keys:
- "action": string describing the action (e.g. "escalate_to_maintenance", "auto_resolve", "ignore", "scale_up")
- "confidence": float between 0 and 1
- "reasoning": one-sentence explanation
""",
        )

        if not USE_MOCK_LLM:
            self.llm = ChatOpenAI(model=LLM_MODEL, temperature=0.2)
            self.chain = self.routing_prompt | self.llm | JsonOutputParser()
        else:
            self.llm = None
            self.chain = None

    def route_event(self, event_data: dict, historical_context: list) -> dict:
        try:
            context_str = json.dumps(historical_context, default=str) if historical_context else "None"
            event_str = json.dumps(event_data, default=str)

            if self.chain:
                result = self.chain.invoke({
                    "event_data": event_str,
                    "historical_context": context_str,
                })
                return {"decision": result}

            return {
                "decision": {
                    "action": "escalate_to_maintenance",
                    "confidence": 0.92,
                    "reasoning": "Mock response — set USE_MOCK_LLM=false and provide OPENAI_API_KEY to enable real LLM routing",
                }
            }
        except Exception:
            logger.exception("Routing failed")
            return {"decision": {"action": "escalate_to_maintenance", "confidence": 0.5, "reasoning": "Fallback due to LLM error"}}

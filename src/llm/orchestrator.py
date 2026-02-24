from langchain.prompts import PromptTemplate
import os
import json
from dotenv import load_dotenv

load_dotenv()

class Orchestrator:
    def __init__(self):
        # We bypass ChatOpenAI for the local prototype to avoid Pydantic/OpenAI validation crashes
        self.routing_prompt = PromptTemplate(
            input_variables=["event_data", "historical_context"],
            template="""You are a strategic routing agent in a distributed decision engine.

Received an event:
{event_data}

Historical context for similar events:
{historical_context}

Based on this, what immediate technical action should be taken? 
Format your response as a JSON dictionary with 'action' (string) and 'confidence' (float, 0-1) keys.
"""
        )

    def route_event(self, event_data: dict, historical_context: list) -> dict:
        try:
            # Format the prompt to show it is being populated with context
            prompt_text = self.routing_prompt.format(
                event_data=str(event_data),
                historical_context=str(historical_context) if historical_context else "None"
            )
            
            # Return a mocked semantic routing decision for Phase 1 verification
            mock_response = json.dumps({"action": "escalate_to_maintenance", "confidence": 0.92})
            return {"raw_decision": mock_response}
        except Exception as e:
            return {"error": str(e)}

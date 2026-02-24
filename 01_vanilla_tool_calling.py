import json

# =====================================================================
# This script simulates the exact process of "Tool Calling". 
# It proves that an LLM doesn't actually "run" code; it just 
# generates JSON that your Python script catches and executes.
# =====================================================================

# 1. The Python Tool (The function we want the LLM to use)
def get_sensor_data(sensor_id: str) -> dict:
    """Simulates fetching real-time data from a database or API."""
    print(f"\n[SYSTEM: Executing Python function 'get_sensor_data' for {sensor_id}...]")
    
    # Mock database lookup
    database = {
        "engine_5": {"temperature_celsius": 105, "status": "critical_overheating"},
        "engine_2": {"temperature_celsius": 45, "status": "normal"}
    }
    
    return database.get(sensor_id, {"error": "Sensor not found"})

# 2. The Mock LLM Interaction (What happens over the network)
def simulate_llm_api_call(chat_history: list) -> str:
    """
    Simulates sending the chat history to an LLM provider (OpenAI, Gemini, vLLM).
    In reality, this is an HTTP request. For learning, we hardcode the response.
    """
    print("\n[SYSTEM: Sending Request to LLM...]")
    
    last_message = chat_history[-1]["content"]
    
    # The LLM reads the user ask and predicts it needs the tool.
    if "Why is engine_5 failing" in last_message:
        # The LLM generates THIS JSON string. It executes nothing.
        llm_response = """
        {
            "tool_call": {
                "name": "get_sensor_data",
                "arguments": {
                    "sensor_id": "engine_5"
                }
            }
        }
        """
        return llm_response.strip()
    
    # If the LLM has already seen the sensor data in the history...
    if any("105" in str(msg) for msg in chat_history):
        return "Based on the sensor data, engine_5 is failing because its temperature is 105 degree Celsius, which is critical overheating. Recommend immediate shutdown."
        
    return "I don't have enough information."

# 3. The Orchestration Loop (What LangChain does under the hood)
def run_agent_loop(user_query: str):
    print("="*60)
    print(f"USER QUERY: {user_query}")
    print("="*60)
    
    # We maintain a conversation history
    chat_history = [
        {"role": "system", "content": "You are a diagnostic AI. You have access to the tool 'get_sensor_data'."},
        {"role": "user", "content": user_query}
    ]
    
    # Step A: Ask the LLM
    response_text = simulate_llm_api_call(chat_history)
    print(f"\n[LLM RAW OUTPUT]:\n{response_text}")
    
    # Step B: Check if the LLM spit out a Tool Call (JSON)
    if "tool_call" in response_text:
        # We parse the text into a Python dictionary
        parsed_json = json.loads(response_text)
        tool_name = parsed_json["tool_call"]["name"]
        tool_args = parsed_json["tool_call"]["arguments"]
        
        # Step C: WE run the actual Python code
        if tool_name == "get_sensor_data":
            # Extract arguments and call the function
            sensor_id = tool_args["sensor_id"]
            observation = get_sensor_data(sensor_id)
            print(f"[SYSTEM: Tool returned data]: {observation}")
            
            # Step D: Append the observation to the history and ask the LLM again
            chat_history.append({"role": "assistant", "content": response_text})
            chat_history.append({"role": "tool_result", "content": str(observation)})
            
            # Second call to the LLM, now armed with the real data
            final_response = simulate_llm_api_call(chat_history)
            print(f"\n[LLM FINAL ANSWER]:\n{final_response}")

if __name__ == "__main__":
    run_agent_loop("Why is engine_5 failing?")

import requests
import json
from tools import AVAILABLE_TOOLS

# Configuration
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5-coder" # Swap to your preferred local model

# ==========================================
# 1. TOOLS (auto-loaded from tools/ package)
# ==========================================
# AVAILABLE_TOOLS is imported above from tools/__init__.py
# To add a new tool, just create a new file in the tools/ directory.

# ==========================================
# 2. THE SYSTEM PROMPT
# ==========================================
# This strict prompt forces the LLM to output ONLY JSON when it wants a tool.
SYSTEM_PROMPT = """You are a helpful, minimal local AI assistant.
You have access to the following tools:
- trigger_esp32_relay(device_ip: str, action: str)
- read_local_logs()
- get_time_date()
- list_folder_contents(path: str)

If you need to use a tool to fulfill the user's request, output ONLY a JSON object exactly like this:
{"tool": "function_name", "kwargs": {"argument": "value"}}

Do NOT add any other text, markdown formatting, or explanations when calling a tool.
If you do not need a tool, answer the user normally in plain text.
"""

# ==========================================
# 3. THE EXECUTION LOOP
# ==========================================
def main():
    print(f"Starting Local Agent using {MODEL} (Type 'exit' to quit)\n")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit']:
            break
            
        messages.append({"role": "user", "content": user_input})
        
        while True:
            # 1. Ask Ollama what to do next
            payload = {"model": MODEL, "messages": messages, "stream": False}
            try:
                response = requests.post(OLLAMA_URL, json=payload).json()
                bot_reply = response["message"]["content"].strip()
            except Exception as e:
                print(f"\n[Error connecting to Ollama] {e}")
                break

            # Strip markdown code fences if the model wrapped the JSON (e.g. ```json ... ```)
            clean_reply = bot_reply
            if bot_reply.startswith("```"):
                lines = bot_reply.splitlines()
                # Drop the opening fence line and closing fence line
                inner = lines[1:] if lines[0].startswith("```") else lines
                if inner and inner[-1].strip() == "```":
                    inner = inner[:-1]
                clean_reply = "\n".join(inner).strip()

            # 2. Intercept JSON Tool Calls
            if clean_reply.startswith("{") and "tool" in clean_reply:
                try:
                    tool_call = json.loads(clean_reply)
                    tool_name = tool_call.get("tool")
                    kwargs = tool_call.get("kwargs", {})
                    
                    if tool_name in AVAILABLE_TOOLS:
                        # Run the actual python function safely on your machine
                        result = AVAILABLE_TOOLS[tool_name](**kwargs)
                        print(f"   [System Result] -> {result}\n")
                        
                        # Add the model's tool call and the system's result to the chat history
                        messages.append({"role": "assistant", "content": bot_reply})
                        messages.append({"role": "user", "content": f"Tool execution result: {result}"})
                        
                        # CONTINUE the inner loop so the model can read the result and respond
                        continue
                    else:
                        print(f"\n   [Error] -> Model hallucinated an unknown tool: {tool_name}")
                        break
                except json.JSONDecodeError:
                    print("\n   [Error] -> Model generated malformed JSON.")
                    break
            
            # 3. Final Output
            # If the response doesn't start with '{', it's a regular text response.
            print(f"Agent: {bot_reply}")
            messages.append({"role": "assistant", "content": bot_reply})
            break # Exit the inner tool loop, wait for next user input

if __name__ == "__main__":
    main()
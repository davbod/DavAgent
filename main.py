import os
import re
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
def _load_memory_context() -> str:
    """Reads memory.md and returns its content, or empty string if not found."""
    memory_path = os.path.join(os.path.dirname(__file__), "memory.md")
    if os.path.exists(memory_path):
        with open(memory_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            return f"\n\n## Memory from previous sessions:\n{content}\n"
    return ""


BASE_SYSTEM_PROMPT = """You are a helpful, minimal local AI assistant.
You have access to the following tools:
- trigger_esp32_relay(device_ip: str, action: str)
- read_local_logs()
- get_time_date()
- list_folder_contents(path: str)
- save_memory(summary: str)         — call this when the user asks you to remember or save the conversation
- load_memory()                     — call this to read notes from previous sessions
- create_file(path: str, content: str = "")          — create a new file with optional content
- create_folder(path: str)                           — create a new folder
- delete_file(path: str)                             — delete a single file
- delete_folder(path: str)                           — delete a folder and all its contents
- read_file(path: str)                               — read the text content of a file
- write_file(path: str, content: str, mode: str)     — write/overwrite or append to a file (mode: 'overwrite' or 'append')
- list_directory(path: str = ".")                    — list files and folders in a directory
- search_files(path: str, pattern: str, search_content: str) — search for files by name pattern and/or text content

If you need to use a tool to fulfill the user's request, output ONLY one or more JSON tool-call objects like this:
{"tool": "function_name", "kwargs": {"argument": "value"}}

Rules:
- Output ONLY JSON when calling tools — no surrounding text, markdown, or explanations.
- You may output MULTIPLE tool calls in a single response when the steps are independent.
  Each tool call must be a separate JSON object on its own line.
- After each batch of tool calls you will receive all results together, then respond to the user.
- If you do not need a tool, answer the user normally in plain text."""

SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + _load_memory_context()

def _extract_all_tool_calls(text: str) -> list[dict]:
    """Extracts ALL tool-call JSON objects from anywhere in the model reply.

    Handles:
      - Clean JSON:              {"tool": ..., "kwargs": {...}}
      - Surrounded by text:      "Step 1: {...} Step 2: {...}"
      - Wrapped in code fences:  ```json\n{"tool": ...}\n```
    Returns a deduplicated list of parsed tool-call dicts (in order of appearance).
    """
    candidates = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}', text, re.DOTALL)
    tool_calls = []
    seen = set()
    for candidate in candidates:
        try:
            obj = json.loads(candidate)
            if "tool" in obj:
                key = json.dumps(obj, sort_keys=True)
                if key not in seen:
                    seen.add(key)
                    tool_calls.append(obj)
        except json.JSONDecodeError:
            pass
    return tool_calls


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

            # 2. Extract ALL tool calls from this reply and run them
            tool_calls = _extract_all_tool_calls(bot_reply)
            if tool_calls:
                messages.append({"role": "assistant", "content": bot_reply})
                batch_results = []

                for tool_call in tool_calls:
                    tool_name = tool_call.get("tool")
                    kwargs = tool_call.get("kwargs", {})

                    if tool_name in AVAILABLE_TOOLS:
                        result = AVAILABLE_TOOLS[tool_name](**kwargs)
                        print(f"   [System Result] -> {result}\n")
                        batch_results.append(f"[{tool_name}] {result}")
                    else:
                        err = f"Error: Unknown tool '{tool_name}'"
                        print(f"\n   [Error] -> Model hallucinated an unknown tool: {tool_name}")
                        batch_results.append(err)

                # Return all results together so the model can summarise
                combined = "\n".join(batch_results)
                messages.append({"role": "user", "content": f"Tool results:\n{combined}"})
                continue  # Let the model read results and respond

            # 3. Final Output — no tool calls found, treat as plain text response
            print(f"Agent: {bot_reply}")
            messages.append({"role": "assistant", "content": bot_reply})
            break  # Exit inner loop, wait for next user input

if __name__ == "__main__":
    main()
import os
import requests
import json
import time
import shutil
import subprocess
from tools import AVAILABLE_TOOLS, TOOL_SCHEMAS

# Configuration
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_URL = OLLAMA_HOST + "/api/chat"
MODEL = "qwen3:30b-a3b" # Swap to your preferred local model


# ==========================================
# 0. STARTUP: ensure Ollama is up and the model is available
# ==========================================
def _server_is_up() -> bool:
    """Returns True if the Ollama HTTP API is responding."""
    try:
        requests.get(OLLAMA_HOST, timeout=2)
        return True
    except requests.RequestException:
        return False


def _model_available() -> bool:
    """Returns True if MODEL is present in the local Ollama model list."""
    try:
        tags = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5).json()
    except requests.RequestException:
        return False
    names = {m.get("name", "") for m in tags.get("models", [])}
    # Match the exact tag, or the base name (before ':') for convenience.
    base = MODEL.split(":")[0]
    return MODEL in names or any(n.split(":")[0] == base for n in names)


def ensure_ollama_running() -> bool:
    """Makes sure `ollama serve` is up, starting it silently if needed.

    Returns True once the server is reachable, False if it can't be started.
    """
    if _server_is_up():
        return True

    ollama_bin = shutil.which("ollama")
    if not ollama_bin:
        print("[Error] 'ollama' not found on PATH. Install it or start the server manually.")
        return False

    # Launch detached so the server survives this process and stays quiet.
    subprocess.Popen(
        [ollama_bin, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    # Poll for readiness (up to ~15s).
    for _ in range(30):
        if _server_is_up():
            return True
        time.sleep(0.5)

    print("[Error] Ollama server did not become ready in time.")
    return False


def _warm_up_model() -> None:
    """Loads MODEL into memory so the first user message isn't slow. Best-effort."""
    try:
        requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json={"model": MODEL, "prompt": "", "stream": False, "keep_alive": "30m"},
            timeout=120,
        )
    except requests.RequestException:
        pass


def _chat(messages):
    """Runs one streaming chat turn. Returns (content, tool_calls).

    Uses Ollama's native function-calling: the tool schemas are sent in the
    `tools` field and the model replies with a structured `tool_calls` list
    (name + already-parsed arguments) instead of us regex-scraping JSON out of
    the text. `tool_calls` is [] on a plain conversational turn.

    Why streaming: qwen3 spends most of a turn generating reasoning tokens.
    With stream=False the console sits in dead air until the turn finishes;
    streaming lets us show a live indicator so it feels as responsive as
    `ollama run`.

    Why think=True: reasoning goes to a separate `thinking` field we ignore, so
    `content` stays clean with no <think> tags to scrub.
    """
    payload = {
        "model": MODEL,
        "messages": messages,
        "tools": TOOL_SCHEMAS,
        "stream": True,
        "think": True,
        "keep_alive": "30m",  # keep the 18GB model resident between turns
    }
    content = ""
    tool_calls = []
    label = "thinking"
    shown = False
    with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=300) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            msg = json.loads(line).get("message", {})
            if msg.get("content"):
                content += msg["content"]
                label = "generating"
            if msg.get("tool_calls"):
                tool_calls.extend(msg["tool_calls"])
            print(f"\r   ({label}…)   ", end="", flush=True)
            shown = True
    if shown:
        print("\r" + " " * 18 + "\r", end="", flush=True)  # clear the indicator line
    return content.strip(), tool_calls

# ==========================================
# 1. TOOLS (auto-loaded from tools/ package)
# ==========================================
# AVAILABLE_TOOLS is imported above from tools/__init__.py
# To add a new tool, just create a new file in the tools/ directory.

# ==========================================
# 2. THE SYSTEM PROMPT
# ==========================================
# Tools are advertised to the model via Ollama's native `tools` schema field
# (see tools/__init__.py), so the prompt no longer needs to list them or coax
# JSON out of the model — it just sets the assistant's persona and loads memory.
def _load_memory_context() -> str:
    """Reads memory.md and returns its content, or empty string if not found."""
    memory_path = os.path.join(os.path.dirname(__file__), "memory.md")
    if os.path.exists(memory_path):
        with open(memory_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            return f"\n\n## Memory from previous sessions:\n{content}\n"
    return ""


BASE_SYSTEM_PROMPT = """You are a helpful, minimal local AI assistant with \
access to tools for the local filesystem, persistent memory, the current \
time/date, and hardware control. Use a tool when it helps fulfil the user's \
request; otherwise answer directly and concisely. Call save_memory when the \
user asks you to remember something, and load_memory to recall earlier notes."""

SYSTEM_PROMPT = BASE_SYSTEM_PROMPT + _load_memory_context()


# ==========================================
# 3. THE EXECUTION LOOP
# ==========================================
def main():
    if not ensure_ollama_running():
        return
    if not _model_available():
        print(f"[Warning] Model '{MODEL}' not found locally. Run: ollama pull {MODEL}")
    else:
        _warm_up_model()

    print(f"Starting Local Agent using {MODEL} (Type 'exit' to quit)\n")
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['exit', 'quit']:
            break

        messages.append({"role": "user", "content": user_input})

        while True:
            # Refresh memory into the system prompt each turn so anything the
            # model just saved via save_memory is visible on the very next turn
            # (SYSTEM_PROMPT is only built once at startup).
            messages[0]["content"] = BASE_SYSTEM_PROMPT + _load_memory_context()

            # 1. Ask Ollama what to do next (streamed, with a live indicator).
            try:
                bot_reply, tool_calls = _chat(messages)
            except Exception as e:
                print(f"\n[Error connecting to Ollama] {e}")
                break

            # 2. Run any native tool calls the model requested.
            if tool_calls:
                # Echo the model's own tool_calls back into history so it can
                # correlate each result with the request it made.
                messages.append({
                    "role": "assistant",
                    "content": bot_reply,
                    "tool_calls": tool_calls,
                })

                for tool_call in tool_calls:
                    fn = tool_call.get("function", {})
                    tool_name = fn.get("name")
                    kwargs = fn.get("arguments") or {}

                    if tool_name in AVAILABLE_TOOLS:
                        try:
                            result = AVAILABLE_TOOLS[tool_name](**kwargs)
                        except Exception as e:
                            result = f"Error running {tool_name}: {e}"
                        print(f"   [System Result] -> {result}\n")
                    else:
                        result = f"Error: Unknown tool '{tool_name}'"
                        print(f"\n   [Error] -> Model requested an unknown tool: {tool_name}")

                    # Feed the result back as a proper tool-role message.
                    messages.append({
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": str(result),
                    })

                continue  # Let the model read the results and respond

            # 3. Final Output — no tool calls, treat as a plain text response.
            print(f"Agent: {bot_reply}")
            messages.append({"role": "assistant", "content": bot_reply})
            break  # Exit inner loop, wait for next user input

if __name__ == "__main__":
    main()
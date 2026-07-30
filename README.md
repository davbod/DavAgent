# DavAgent
A low profile, simple, local LLM powered, moddable agent assistant.

## Project Structure
- `main.py` – Core execution loop, tool registration, and system prompt handling.
- `memory.md` – Persistent conversation memory, refreshed into the system prompt at the start of every turn.
- `tools/` – Package containing utility tools:
  - `memory.py` – Save/load conversation memory.
  - `filesystem.py` – Comprehensive file & folder creation, deletion, browsing, searching, reading, and writing.
  - `time_date.py` – Retrieves current time and date.
  - `local_logs.py` – Collects recent system logs and CPU metrics (cross-platform: Windows/macOS/Linux).
- `.git/`, `.gitignore`, `LICENSE` – Standard repository metadata.

## Available Tools (auto‑loaded)
- `read_local_logs()`
- `get_time_date()`
- `save_memory(summary: str)`
- `load_memory()`
- `create_file(path: str, content: str = "")`
- `create_folder(path: str)`
- `delete_file(path: str)`
- `delete_folder(path: str)`
- `read_file(path: str)`
- `write_file(path: str, content: str, mode: str)`
- `list_directory(path: str = ".")`
- `search_files(path: str, pattern: str, search_content: str)`

## How tools work
Tools are exposed to the model via **Ollama native function-calling**: the JSON
schema for each tool is generated automatically from its function signature
(parameter names, types, defaults) and Google-style docstring (`tools/__init__.py`),
then passed to Ollama in the `tools` field. The model replies with a structured
`tool_calls` list, which the agent executes and feeds back as `tool`-role
messages. There is no prompt-based JSON coaxing or regex parsing.

To add a tool: drop a `.py` file in `tools/`, give the function type hints and a
docstring, and export `TOOLS = {"name": fn}`. The schema is picked up automatically.

## Usage
Run the agent:
```bash
python main.py
```
The agent auto-starts the Ollama server if it isn't already running, keeps the
model resident between turns, and shows a live `(thinking…)` indicator while the
model works. Interact via the console; type `exit` to quit.

---

*Generated on 2026-07-19 12:55*

# DavAgent
A low profile, simple, local LLM powered, moddable agent assistant.

## Project Structure
- `main.py` – Core execution loop, tool registration, and system prompt handling.
- `memory.md` – Persistent conversation memory, refreshed into the system prompt at the start of every turn.
- `library/` – Persistent research/knowledge base (markdown entries + a regenerable `index.json`). Not injected into every prompt like `memory.md` — retrieved on demand via `search_library`. See "Memory vs. Library" below.
- `tools/` – Package containing utility tools:
  - `memory.py` – Save/load conversation memory.
  - `library.py` – Save/search the research library using local semantic embeddings.
  - `web.py` – Fetch a web page's readable text content.
  - `filesystem.py` – Comprehensive file & folder creation, deletion, browsing, searching, reading, and writing.
  - `time_date.py` – Retrieves current time and date.
  - `local_logs.py` – Collects recent system logs and CPU metrics (cross-platform: Windows/macOS/Linux).
- `tests/` – pytest suite covering every tool and `main.py`'s Ollama-connectivity logic.
- `.git/`, `.gitignore`, `LICENSE` – Standard repository metadata.

## Memory vs. Library
Two different persistence mechanisms, used for different things:
- **Memory** (`memory.md`, `save_memory`/`load_memory`) — small, always injected into the system prompt every turn. For conversational continuity: preferences, ongoing threads, things you explicitly ask it to remember.
- **Library** (`library/`, `save_to_library`/`search_library`) — unbounded in size, never injected wholesale. The agent saves research and learnings here on its own initiative (and tells you when it does), then retrieves relevant entries via semantic search only when a query calls for it. Each entry is a markdown file with frontmatter; `library/index.json` holds the embedding vectors used for ranking and is gitignored (regenerate it with `rebuild_library_index` if it's missing).

Library search uses a small local Ollama embedding model, **not** the chat model:
```bash
ollama pull all-minilm
```

## Available Tools (auto‑loaded)
- `read_local_logs()`
- `get_time_date()`
- `save_memory(summary: str)`
- `load_memory()`
- `save_to_library(title: str, content: str, tags: str = "")`
- `search_library(query: str, top_k: int = 5)`
- `rebuild_library_index()`
- `fetch_url(url: str, max_chars: int = 4000)`
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

## Setup
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt  # or requirements.txt to skip pytest
```
`requirements.txt` pins `urllib3<2` — on macOS, the system Python
(`/usr/bin/python3`) links against LibreSSL rather than OpenSSL, and urllib3
v2 emits a `NotOpenSSLWarning` on import under that combination. Pinning
below v2 avoids it without needing a different Python install.

## Testing
```bash
python -m pytest
```
All tool logic is tested with mocked filesystem/network/subprocess calls — no
running Ollama server or pulled model is required to run the suite.

---

*Generated on 2026-07-19 12:55*

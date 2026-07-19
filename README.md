# DavAgent
A low profile, simple, local LLM powered, moddable agent assistant.

## Project Structure
- `main.py` – Core execution loop, tool registration, and system prompt handling.
- `memory.md` – Persistent conversation memory that is loaded into the system prompt on startup.
- `tools/` – Package containing utility tools:
  - `folder_contents.py` – Lists folder contents.
  - `memory.py` – Save/load conversation memory.
  - `filesystem.py` – Comprehensive file & folder creation, deletion, browsing, searching, reading, and writing.
  - `time_date.py` – Retrieves current time and date.
- `.git/`, `.gitignore`, `LICENSE` – Standard repository metadata.

## Available Tools (auto‑loaded)
- `trigger_esp32_relay(device_ip: str, action: str)`
- `read_local_logs()`
- `get_time_date()`
- `list_folder_contents(path: str)`
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

## Usage
Run the agent:
```bash
python main.py
```
Interact via the console; the agent will suggest tool calls as JSON objects, execute them, and return results.

---

*Generated on 2026-07-19 12:55*

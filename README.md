# DavAgent
A low profile, simple, local LLM powered, moddable agent assistant.

## Project Structure
- `main.py` – Core execution loop, tool registration, and system prompt handling.
- `memory.md` – Persistent conversation memory that is loaded into the system prompt on startup.
- `tools/` – Package containing utility tools:
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

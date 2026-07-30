import os
import datetime
from typing import Dict

# Path to the memory file (memory.md) located at the project root
MEMORY_FILE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "memory.md"))


def _ensure_memory_file_exists() -> None:
    """Create the memory file if it does not exist."""
    os.makedirs(os.path.dirname(MEMORY_FILE_PATH), exist_ok=True)
    if not os.path.exists(MEMORY_FILE_PATH):
        with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
            f.write("")


def _read_memory_file() -> str:
    """Read the entire memory file content."""
    _ensure_memory_file_exists()
    with open(MEMORY_FILE_PATH, "r", encoding="utf-8") as f:
        return f.read()


def _append_to_memory(content: str) -> None:
    """Append a new entry to the memory file with a timestamp."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"## [{timestamp}]\n{content}\n\n---\n\n"
    with open(MEMORY_FILE_PATH, "a", encoding="utf-8") as f:
        f.write(entry)


def memory(action: str, target: str = "memory", content: str = "", replacement: str = "") -> Dict:
    """Unified memory tool operating on the simple file‑based store.

    Parameters
    ----------
    action: "add", "replace", or "remove"
    target: currently ignored (kept for compatibility)
    content: For "add" – the entry to add; for "remove" – the needle to match; for "replace" – the needle to match.
    replacement: Only used with "replace" – the new entry text.
    """
    if action == "add":
        _append_to_memory(content)
        return {"success": True, "added": True}
    elif action == "remove":
        data = _read_memory_file()
        lines = data.splitlines()
        filtered = [line for line in lines if content not in line]
        new_content = "\n".join(filtered) + "\n"
        with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        return {"success": True, "removed": True}
    elif action == "replace":
        data = _read_memory_file()
        if content in data:
            new_data = data.replace(content, replacement)
            with open(MEMORY_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(new_data)
            return {"success": True, "replaced": True}
        else:
            return {"success": False, "error": "Pattern not found"}
    else:
        return {"success": False, "error": f"Unsupported action {action}"}


def get_memory_snapshot() -> str:
    """Return the current memory content suitable for injection into the system prompt."""
    return _read_memory_file()

# ---- Legacy wrappers -----------------------------------------------------

def save_memory(summary: str) -> str:
    """Legacy wrapper used by older agents. Adds a new entry to MEMORY.md."""
    res = memory("add", target="memory", content=summary)
    return "saved" if res.get("success") else f"Error: {res.get('error')}"


def load_memory() -> str:
    """Legacy wrapper – returns the current snapshot (read‑only view)."""
    return get_memory_snapshot()

# Export the tool dict expected by tools/__init__.py
TOOLS = {
    "save_memory": save_memory,
    "load_memory": load_memory,
}

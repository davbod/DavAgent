import os
from datetime import datetime

MEMORY_FILE = os.path.join(os.path.dirname(__file__), "..", "memory.md")


def save_memory(summary: str) -> str:
    """Saves a summary of the current conversation to memory.md for future sessions.

    Args:
        summary: A concise summary of the current conversation to persist.

    Returns:
        A confirmation string.
    """
    print(f"\n   [Executing] -> Saving memory...")

    try:
        abs_path = os.path.abspath(MEMORY_FILE)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        # Read existing content if file exists
        existing = ""
        if os.path.exists(abs_path):
            with open(abs_path, "r", encoding="utf-8") as f:
                existing = f.read().strip()

        # Prepend the new entry so most recent is at the top
        new_entry = f"## [{timestamp}]\n{summary.strip()}\n"
        content = f"{new_entry}\n---\n\n{existing}" if existing else new_entry

        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Memory saved successfully to {abs_path}"

    except Exception as e:
        return f"Error saving memory: {e}"


def load_memory() -> str:
    """Reads the contents of memory.md.

    Returns:
        The memory file contents, or a message if no memory exists yet.
    """
    print(f"\n   [Executing] -> Loading memory...")

    try:
        abs_path = os.path.abspath(MEMORY_FILE)
        if not os.path.exists(abs_path):
            return "No memory file found. This appears to be a fresh session."

        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        return content if content else "Memory file is empty."

    except Exception as e:
        return f"Error loading memory: {e}"


TOOLS = {
    "save_memory": save_memory,
    "load_memory": load_memory,
}

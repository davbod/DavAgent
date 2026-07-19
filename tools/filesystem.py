import os
import shutil
import fnmatch
from datetime import datetime


# ---------------------------------------------------------------------------
# CREATE
# ---------------------------------------------------------------------------

def create_file(path: str, content: str = "") -> str:
    """Creates a new file at the given path with optional initial content.

    Args:
        path: The path of the file to create.
        content: Optional text content to write into the file.

    Returns:
        A confirmation or error string.
    """
    print(f"\n   [Executing] -> Creating file: {path}")
    try:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return f"Error: File already exists at '{abs_path}'. Use write_file to overwrite."
        os.makedirs(os.path.dirname(abs_path), exist_ok=True)
        with open(abs_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"File created successfully: {abs_path}"
    except Exception as e:
        return f"Error creating file: {e}"


def create_folder(path: str) -> str:
    """Creates a new folder (and any missing parent folders) at the given path.

    Args:
        path: The directory path to create.

    Returns:
        A confirmation or error string.
    """
    print(f"\n   [Executing] -> Creating folder: {path}")
    try:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return f"Error: Path already exists: '{abs_path}'"
        os.makedirs(abs_path)
        return f"Folder created successfully: {abs_path}"
    except Exception as e:
        return f"Error creating folder: {e}"


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------

def delete_file(path: str) -> str:
    """Deletes a single file at the given path.

    Args:
        path: The path of the file to delete.

    Returns:
        A confirmation or error string.
    """
    print(f"\n   [Executing] -> Deleting file: {path}")
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Error: File not found: '{abs_path}'"
        if not os.path.isfile(abs_path):
            return f"Error: '{abs_path}' is a directory. Use delete_folder instead."
        os.remove(abs_path)
        return f"File deleted: {abs_path}"
    except Exception as e:
        return f"Error deleting file: {e}"


def delete_folder(path: str) -> str:
    """Deletes a folder and all of its contents recursively.

    Args:
        path: The directory path to delete.

    Returns:
        A confirmation or error string.
    """
    print(f"\n   [Executing] -> Deleting folder: {path}")
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Error: Folder not found: '{abs_path}'"
        if not os.path.isdir(abs_path):
            return f"Error: '{abs_path}' is a file. Use delete_file instead."
        shutil.rmtree(abs_path)
        return f"Folder and all contents deleted: {abs_path}"
    except Exception as e:
        return f"Error deleting folder: {e}"


# ---------------------------------------------------------------------------
# READ & WRITE
# ---------------------------------------------------------------------------

def read_file(path: str) -> str:
    """Reads and returns the text content of a file.

    Args:
        path: The path of the file to read.

    Returns:
        The file contents as a string, or an error message.
    """
    print(f"\n   [Executing] -> Reading file: {path}")
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Error: File not found: '{abs_path}'"
        if not os.path.isfile(abs_path):
            return f"Error: '{abs_path}' is a directory, not a file."
        with open(abs_path, "r", encoding="utf-8") as f:
            content = f.read()
        size = os.path.getsize(abs_path)
        return f"--- {abs_path} ({size} bytes) ---\n{content}"
    except UnicodeDecodeError:
        return f"Error: '{path}' appears to be a binary file and cannot be read as text."
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(path: str, content: str, mode: str = "overwrite") -> str:
    """Writes text content to a file.

    Args:
        path: The path of the file to write.
        content: The text to write.
        mode: 'overwrite' to replace the file, 'append' to add to the end.

    Returns:
        A confirmation or error string.
    """
    print(f"\n   [Executing] -> Writing file ({mode}): {path}")
    try:
        abs_path = os.path.abspath(path)
        os.makedirs(os.path.dirname(abs_path) or ".", exist_ok=True)
        write_mode = "a" if mode == "append" else "w"
        with open(abs_path, write_mode, encoding="utf-8") as f:
            f.write(content)
        action = "appended to" if mode == "append" else "written to"
        return f"Content {action}: {abs_path}"
    except Exception as e:
        return f"Error writing file: {e}"


# ---------------------------------------------------------------------------
# LIST / BROWSE
# ---------------------------------------------------------------------------

def list_directory(path: str = ".") -> str:
    """Lists the contents of a directory with file sizes and folder counts.

    Args:
        path: The directory path to list. Defaults to current directory.

    Returns:
        A formatted string listing all files and subdirectories.
    """
    print(f"\n   [Executing] -> Listing directory: {path}")
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Error: Path not found: '{abs_path}'"
        if not os.path.isdir(abs_path):
            return f"Error: '{abs_path}' is a file, not a directory."

        entries = os.listdir(abs_path)
        if not entries:
            return f"Directory is empty: {abs_path}"

        folders, files = [], []
        for name in sorted(entries, key=lambda x: x.lower()):
            full = os.path.join(abs_path, name)
            if os.path.isdir(full):
                count = len(os.listdir(full))
                folders.append(f"  [DIR]  {name}/  ({count} items)")
            else:
                size = os.path.getsize(full)
                mtime = datetime.fromtimestamp(os.path.getmtime(full)).strftime("%Y-%m-%d %H:%M")
                files.append(f"  [FILE] {name}  ({size} bytes, modified {mtime})")

        lines = [f"Contents of '{abs_path}':"]
        lines.extend(folders)
        lines.extend(files)
        lines.append(f"\nTotal: {len(folders)} folder(s), {len(files)} file(s).")
        return "\n".join(lines)
    except PermissionError:
        return f"Error: Permission denied: '{path}'"
    except Exception as e:
        return f"Error listing directory: {e}"


# ---------------------------------------------------------------------------
# SEARCH
# ---------------------------------------------------------------------------

def search_files(path: str = ".", pattern: str = "*", search_content: str = "") -> str:
    """Searches for files by name pattern and/or text content within a directory tree.

    Args:
        path: The root directory to search from. Defaults to current directory.
        pattern: A glob pattern for filenames (e.g. '*.py', 'report*'). Defaults to '*'.
        search_content: Optional text to search for inside matching files.

    Returns:
        A formatted list of matches, or a message if nothing was found.
    """
    print(f"\n   [Executing] -> Searching in '{path}' for pattern='{pattern}'" +
          (f", content='{search_content}'" if search_content else ""))
    try:
        abs_path = os.path.abspath(path)
        if not os.path.exists(abs_path):
            return f"Error: Path not found: '{abs_path}'"

        matches = []
        for root, dirs, files in os.walk(abs_path):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for filename in files:
                if fnmatch.fnmatch(filename, pattern):
                    full = os.path.join(root, filename)
                    rel = os.path.relpath(full, abs_path)
                    if search_content:
                        try:
                            with open(full, "r", encoding="utf-8", errors="ignore") as f:
                                text = f.read()
                            if search_content.lower() in text.lower():
                                # Find the first matching line
                                for i, line in enumerate(text.splitlines(), 1):
                                    if search_content.lower() in line.lower():
                                        matches.append(f"  {rel}  (line {i}: ...{line.strip()[:60]}...)")
                                        break
                        except Exception:
                            pass
                    else:
                        size = os.path.getsize(full)
                        matches.append(f"  {rel}  ({size} bytes)")

        if not matches:
            desc = f"pattern '{pattern}'"
            if search_content:
                desc += f" containing '{search_content}'"
            return f"No files found matching {desc} in '{abs_path}'"

        header = f"Found {len(matches)} match(es) in '{abs_path}':"
        return header + "\n" + "\n".join(matches)

    except Exception as e:
        return f"Error searching files: {e}"


# ---------------------------------------------------------------------------
# TOOL REGISTRY
# ---------------------------------------------------------------------------

TOOLS = {
    "create_file":    create_file,
    "create_folder":  create_folder,
    "delete_file":    delete_file,
    "delete_folder":  delete_folder,
    "read_file":      read_file,
    "write_file":     write_file,
    "list_directory": list_directory,
    "search_files":   search_files,
}

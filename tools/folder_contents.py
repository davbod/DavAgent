import os


def list_folder_contents(path: str = ".") -> str:
    """Lists the contents of a folder at the given path.

    Args:
        path: The directory path to list. Defaults to the current working directory.

    Returns:
        A formatted string listing all files and subdirectories, or an error message.
    """
    print(f"\n   [Executing] -> Listing folder contents of: {path}")

    try:
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            return f"Error: Path '{abs_path}' does not exist."

        if not os.path.isdir(abs_path):
            return f"Error: '{abs_path}' is not a directory."

        entries = os.listdir(abs_path)

        if not entries:
            return f"The folder '{abs_path}' is empty."

        folders = []
        files = []

        for entry in sorted(entries, key=lambda x: x.lower()):
            full_entry = os.path.join(abs_path, entry)
            if os.path.isdir(full_entry):
                folders.append(f"  [DIR]  {entry}/")
            else:
                size = os.path.getsize(full_entry)
                files.append(f"  [FILE] {entry} ({size} bytes)")

        lines = [f"Contents of '{abs_path}':"]
        lines.extend(folders)
        lines.extend(files)
        lines.append(f"\nTotal: {len(folders)} folder(s), {len(files)} file(s).")

        return "\n".join(lines)

    except PermissionError:
        return f"Error: Permission denied when accessing '{path}'."
    except Exception as e:
        return f"Error listing folder contents: {e}"


# The folder_contents tool has been deprecated in favor of the more feature‑rich filesystem.list_directory.
# It remains here for backward compatibility but is not exported.
TOOLS = {}

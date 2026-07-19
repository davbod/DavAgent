import subprocess


def get_time_date():
    """Runs the local PowerShell Get-Date command and returns the current date and time."""
    print("\n   [Executing] -> Running PowerShell Get-Date...")
    result = subprocess.run(
        ["powershell", "-Command", "Get-Date"],
        capture_output=True,
        text=True
    )
    output = result.stdout.strip()
    if result.returncode != 0:
        return f"Error retrieving date/time: {result.stderr.strip()}"
    return f"Current date and time: {output}"


TOOLS = {
    "get_time_date": get_time_date,
}

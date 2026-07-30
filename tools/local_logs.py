import platform
import subprocess


def _run(cmd: list[str], timeout: int = 20) -> str:
    """Runs a command and returns stdout, or a short error string on failure."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return f"(command failed: {result.stderr.strip() or 'no output'})"
        return result.stdout.strip()
    except FileNotFoundError:
        return f"(command not found: {cmd[0]})"
    except Exception as e:
        return f"(error: {e})"


def read_local_logs() -> str:
    """Collects recent system logs and basic performance metrics for this machine.

    Detects the host OS and uses the native tooling for each platform
    (PowerShell on Windows, `log`/`ps` on macOS, `journalctl`/`ps` on Linux),
    so the same tool works everywhere the agent runs.

    Returns:
        A formatted string with recent log entries and top CPU processes, or an
        error message describing what went wrong.
    """
    system = platform.system()
    print(f"\n   [Executing] -> Collecting {system} system diagnostics...")

    if system == "Windows":
        ps_command = (
            "Get-EventLog -LogName System -Newest 15 | "
            "Select-Object TimeGenerated, EntryType, Source | Format-Table -AutoSize | Out-String; "
            "Write-Output '--- Top CPU processes ---'; "
            "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 Id, ProcessName, CPU | "
            "Format-Table -AutoSize | Out-String"
        )
        logs = _run(["powershell", "-NoProfile", "-Command", ps_command], timeout=30)

    elif system == "Darwin":  # macOS
        logs = _run(["log", "show", "--last", "5m", "--style", "compact"], timeout=25)
        # `log show` can be very large; keep the tail, which holds the most recent lines.
        logs = "\n".join(logs.splitlines()[-25:]) or "(no recent log entries)"
        top = _run(["ps", "-Aceo", "pid,%cpu,comm", "-r"], timeout=10)
        top = "\n".join(top.splitlines()[:11])  # header + top 10
        logs = f"{logs}\n\n--- Top CPU processes ---\n{top}"

    else:  # Linux and other POSIX
        logs = _run(["journalctl", "-n", "15", "--no-pager"], timeout=15)
        if logs.startswith("(command not found"):
            logs = _run(["dmesg", "--ctime"], timeout=15)
            logs = "\n".join(logs.splitlines()[-15:])
        top = _run(["ps", "-eo", "pid,%cpu,comm", "--sort=-%cpu"], timeout=10)
        top = "\n".join(top.splitlines()[:11])
        logs = f"{logs}\n\n--- Top CPU processes ---\n{top}"

    return f"=== System Logs & Performance ({system}) ===\n{logs}"


TOOLS = {
    "read_local_logs": read_local_logs,
}

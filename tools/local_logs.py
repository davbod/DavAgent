import subprocess

def read_local_logs():
    """Collects recent Windows system logs and basic performance metrics using PowerShell.
    Returns a formatted string with the captured output or an error message.
    """
    print("\n   [Executing] -> Collecting system diagnostics via PowerShell...")
    # PowerShell command that gathers recent event logs and CPU usage
    ps_command = r"""
        Get-EventLog -LogName System -Newest 20 |
            Select-Object TimeGenerated, EntryType, Source, Message |
            Format-Table -AutoSize -Wrap;
        Write-Host '---';
        Get-Counter -Counter '\Processor(_Total)\% Processor Time' -SampleInterval 1 -MaxSamples 5 |
            Select-Object -ExpandProperty CounterSamples |
            ForEach-Object { $_.CookedValue } |
            Out-String;
        Write-Host '---';
        Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 |
            Format-Table Id, ProcessName, CPU, WorkingSet -AutoSize;
    """
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_command],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return f"Error running diagnostics: {result.stderr.strip()}"
        output = result.stdout.strip()
        return f"=== System Logs & Performance ===\n{output}"
    except Exception as e:
        return f"Exception while collecting logs: {e}"

TOOLS = {
    "read_local_logs": read_local_logs,
}


import subprocess

from tools import local_logs


def test_run_returns_stdout_on_success(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout):
        return subprocess.CompletedProcess(cmd, 0, stdout="output line\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = local_logs._run(["echo", "hi"])
    assert result == "output line"


def test_run_reports_stderr_on_nonzero_exit(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = local_logs._run(["false"])
    assert "command failed" in result
    assert "boom" in result


def test_run_reports_missing_command(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout):
        raise FileNotFoundError()

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = local_logs._run(["nonexistent-binary"])
    assert "command not found: nonexistent-binary" in result


def test_run_reports_timeout_as_generic_error(monkeypatch):
    def fake_run(cmd, capture_output, text, timeout):
        raise subprocess.TimeoutExpired(cmd, timeout)

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = local_logs._run(["slow-command"])
    assert result.startswith("(error:")


def test_read_local_logs_uses_darwin_path_on_macos(monkeypatch):
    monkeypatch.setattr(local_logs.platform, "system", lambda: "Darwin")

    calls = []

    def fake_run(cmd, timeout=20):
        calls.append(cmd)
        if cmd[0] == "log":
            return "log line 1\nlog line 2"
        return "PID %CPU COMM\n1 0.5 init"

    monkeypatch.setattr(local_logs, "_run", fake_run)
    result = local_logs.read_local_logs()
    assert "System Logs & Performance (Darwin)" in result
    assert "log line 2" in result
    assert "Top CPU processes" in result
    assert calls[0][0] == "log"
    assert calls[1][0] == "ps"


def test_read_local_logs_uses_linux_journalctl_path(monkeypatch):
    monkeypatch.setattr(local_logs.platform, "system", lambda: "Linux")

    def fake_run(cmd, timeout=20):
        if cmd[0] == "journalctl":
            return "journal entry"
        return "PID %CPU COMM\n1 0.5 init"

    monkeypatch.setattr(local_logs, "_run", fake_run)
    result = local_logs.read_local_logs()
    assert "journal entry" in result


def test_read_local_logs_falls_back_to_dmesg_when_journalctl_missing(monkeypatch):
    monkeypatch.setattr(local_logs.platform, "system", lambda: "Linux")

    def fake_run(cmd, timeout=20):
        if cmd[0] == "journalctl":
            return "(command not found: journalctl)"
        if cmd[0] == "dmesg":
            return "dmesg line"
        return "PID %CPU COMM\n1 0.5 init"

    monkeypatch.setattr(local_logs, "_run", fake_run)
    result = local_logs.read_local_logs()
    assert "dmesg line" in result

import main


class FakeResponse:
    def __init__(self, json_data=None):
        self._json = json_data or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        pass


def test_server_is_up_true_when_request_succeeds(monkeypatch):
    monkeypatch.setattr(main.requests, "get", lambda *a, **k: FakeResponse())
    assert main._server_is_up() is True


def test_server_is_up_false_on_request_exception(monkeypatch):
    def raiser(*a, **k):
        raise main.requests.RequestException("down")

    monkeypatch.setattr(main.requests, "get", raiser)
    assert main._server_is_up() is False


def test_model_available_matches_exact_tag(monkeypatch):
    monkeypatch.setattr(
        main.requests, "get", lambda *a, **k: FakeResponse({"models": [{"name": main.MODEL}]})
    )
    assert main._model_available() is True


def test_model_available_matches_base_name_before_colon(monkeypatch):
    base = main.MODEL.split(":")[0]
    monkeypatch.setattr(
        main.requests, "get", lambda *a, **k: FakeResponse({"models": [{"name": f"{base}:latest"}]})
    )
    assert main._model_available() is True


def test_model_available_false_when_absent(monkeypatch):
    monkeypatch.setattr(
        main.requests, "get", lambda *a, **k: FakeResponse({"models": [{"name": "other:latest"}]})
    )
    assert main._model_available() is False


def test_model_available_false_on_request_exception(monkeypatch):
    def raiser(*a, **k):
        raise main.requests.RequestException("down")

    monkeypatch.setattr(main.requests, "get", raiser)
    assert main._model_available() is False


def test_ensure_ollama_running_returns_true_immediately_if_already_up(monkeypatch):
    monkeypatch.setattr(main, "_server_is_up", lambda: True)
    assert main.ensure_ollama_running() is True


def test_ensure_ollama_running_returns_false_when_binary_missing(monkeypatch, capsys):
    monkeypatch.setattr(main, "_server_is_up", lambda: False)
    monkeypatch.setattr(main.shutil, "which", lambda name: None)
    assert main.ensure_ollama_running() is False
    assert "not found on PATH" in capsys.readouterr().out


def test_ensure_ollama_running_starts_server_and_waits_for_ready(monkeypatch):
    monkeypatch.setattr(main.shutil, "which", lambda name: "/usr/local/bin/ollama")
    popen_calls = []
    monkeypatch.setattr(main.subprocess, "Popen", lambda *a, **k: popen_calls.append((a, k)))
    monkeypatch.setattr(main.time, "sleep", lambda s: None)

    calls = {"n": 0}

    def fake_server_is_up():
        calls["n"] += 1
        return calls["n"] >= 3  # comes up on the third check

    monkeypatch.setattr(main, "_server_is_up", fake_server_is_up)

    assert main.ensure_ollama_running() is True
    assert popen_calls, "expected `ollama serve` to be launched via subprocess.Popen"


def test_ensure_ollama_running_gives_up_after_polling_times_out(monkeypatch, capsys):
    monkeypatch.setattr(main.shutil, "which", lambda name: "/usr/local/bin/ollama")
    monkeypatch.setattr(main.subprocess, "Popen", lambda *a, **k: None)
    monkeypatch.setattr(main.time, "sleep", lambda s: None)
    monkeypatch.setattr(main, "_server_is_up", lambda: False)

    assert main.ensure_ollama_running() is False
    assert "did not become ready" in capsys.readouterr().out

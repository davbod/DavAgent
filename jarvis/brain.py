"""Brains: the thing that turns a transcript into a reply.

One protocol, two implementations. `ClaudeBrain` shells out to the Claude Code
CLI in headless streaming mode; `EchoBrain` exists so the rest of the pipeline
can be tested with no network and no model.
"""

import json
import os
import shutil
import subprocess
from typing import Iterator, List, Optional, Protocol

DEFAULT_MODEL = "claude-opus-5"
DEFAULT_EFFORT = "low"  # conversation, not deep work — latency matters more

# Phase 1 is conversation only. Anything that reads or writes a real system is
# a phase-4 capability and needs an IT ticket opened first (spec 002, Security
# notes). Left unrestricted, Jarvis went and queried Jira the moment it was
# asked about tickets — observed on the first end-to-end run.
#
# This is a wildcard, deliberately. An enumerated denylist was tried first and
# leaked: denied Bash, it reached the same shell through another tool and ran
# the command anyway. Deny everything; allow back explicitly, per phase.
DENY_ALL_TOOLS = "*"

# Claude writes for a reader by default: markdown, paths, code. Spoken, that is
# unbearable. This resets the register.
VOICE_SYSTEM_PROMPT = (
    "You are Jarvis, answering out loud through a speech synthesiser. "
    "Reply in one to three short spoken sentences. Plain prose only: no "
    "markdown, no bullet points, no code, no file paths, no URLs. "
    "Never say a password, token, key or other credential aloud. "
    "If the answer is long or visual, say the one-line version and offer to put "
    "the detail on screen. Speak British English. "
    "You have no tools in this session: you cannot run commands, read files, or "
    "look anything up. Answer from what you already know, and say plainly when "
    "you do not know rather than guessing. "
    "Never write XML or system tags in your reply — it is read aloud verbatim."
)


def _text_delta(event: dict) -> Optional[str]:
    """The spoken text in a stream event, if it carries any."""
    if event.get("type") != "stream_event":
        return None
    inner = event.get("event", {})
    if inner.get("type") != "content_block_delta":
        return None
    delta = inner.get("delta", {})
    if delta.get("type") == "text_delta" and delta.get("text"):
        return delta["text"]
    return None


def _decode(line: str) -> Optional[dict]:
    """Parse one NDJSON line. A malformed line is skipped, never fatal."""
    line = line.strip()
    if not line:
        return None
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        return None
    return event if isinstance(event, dict) else None


class Brain(Protocol):
    def send(self, text: str) -> Iterator[str]:
        """Yield the reply as text chunks, in order, as they become available."""
        ...


class EchoBrain:
    """Repeats what it heard. For testing the loop without a model."""

    def __init__(self) -> None:
        self.heard: List[str] = []

    def send(self, text: str) -> Iterator[str]:
        self.heard.append(text)
        yield f"You said: {text}"


class ClaudeBrain:
    """Drives `claude -p --output-format stream-json`, one turn per utterance.

    The session id returned on the first turn is fed back via --resume, so a
    conversation carries across utterances instead of restarting cold.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        cwd: Optional[str] = None,
        system_prompt: str = VOICE_SYSTEM_PROMPT,
        binary: Optional[str] = None,
        allowed_tools: Optional[str] = None,
        conversational: bool = True,
        effort: str = DEFAULT_EFFORT,
    ):
        self.model = model
        self.conversational = conversational
        self.effort = effort
        self.cwd = cwd or os.path.expanduser("~")
        self.system_prompt = system_prompt
        self.binary = binary or shutil.which("claude") or "claude"
        self.allowed_tools = allowed_tools
        self.session_id: Optional[str] = None

    def _argv(self, text: str) -> List[str]:
        argv = [
            self.binary,
            "-p", text,
            "--output-format", "stream-json",
            "--include-partial-messages",
            "--verbose",
            "--model", self.model,
            "--effort", self.effort,
            "--append-system-prompt", self.system_prompt,
        ]
        if self.conversational:
            # Belt and braces: deny every tool, and refuse to load MCP servers
            # from the user's settings so no connector sneaks in either.
            argv += ["--disallowed-tools", DENY_ALL_TOOLS]
            argv += ["--strict-mcp-config"]
        if self.allowed_tools:
            argv += ["--allowed-tools", self.allowed_tools]
        if self.session_id:
            argv += ["--resume", self.session_id]
        return argv

    def send(self, text: str) -> Iterator[str]:
        yield from self._parse(self._spawn(text))

    def _spawn(self, text: str) -> Iterator[str]:
        proc = subprocess.Popen(
            self._argv(text),
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            cwd=self.cwd,
        )
        try:
            yield from proc.stdout
        finally:
            proc.stdout.close()
            proc.wait()

    def _parse(self, lines: Iterator[str]) -> Iterator[str]:
        """Turn the NDJSON event stream into text chunks.

        Prefer the incremental text_delta events; fall back to the final result
        only if none arrived, so a reply is never spoken twice.
        """
        saw_delta = False
        for line in lines:
            event = _decode(line)
            if event is None:
                continue

            session_id = event.get("session_id")
            if session_id:
                self.session_id = session_id

            chunk = _text_delta(event)
            if chunk:
                saw_delta = True
                yield chunk
            elif event.get("type") == "result" and not saw_delta:
                result = event.get("result")
                if isinstance(result, str) and result.strip():
                    yield result


class PersistentClaudeBrain:
    """One long-lived CLI process; each utterance is a turn on the same session.

    Spawning a fresh `claude -p` per turn costs 2.5-3.0 s to first token, almost
    all of it session initialisation rather than process startup (the binary
    itself launches in 0.06 s). Holding the process open and feeding it turns
    over stdin drops that to 0.16-1.09 s. Measured, not assumed — see DEVLOG.

    Not thread-safe by design: one voice, one turn at a time.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        cwd: Optional[str] = None,
        system_prompt: str = VOICE_SYSTEM_PROMPT,
        binary: Optional[str] = None,
        conversational: bool = True,
        effort: str = DEFAULT_EFFORT,
    ):
        self.model = model
        self.cwd = cwd or os.path.expanduser("~")
        self.system_prompt = system_prompt
        self.binary = binary or shutil.which("claude") or "claude"
        self.conversational = conversational
        self.effort = effort
        self.session_id: Optional[str] = None
        self._proc: Optional[subprocess.Popen] = None

    def _argv(self) -> List[str]:
        argv = [
            self.binary, "-p",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--include-partial-messages",
            "--verbose",
            "--model", self.model,
            "--effort", self.effort,
            "--append-system-prompt", self.system_prompt,
        ]
        if self.conversational:
            argv += ["--disallowed-tools", DENY_ALL_TOOLS, "--strict-mcp-config"]
        return argv

    def _alive(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def _ensure_running(self) -> None:
        if self._alive():
            return
        self._proc = subprocess.Popen(
            self._argv(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            cwd=self.cwd,
        )

    def send(self, text: str) -> Iterator[str]:
        self._ensure_running()
        payload = {"type": "user", "message": {"role": "user", "content": text}}
        self._proc.stdin.write(json.dumps(payload) + "\n")
        self._proc.stdin.flush()
        return self._read_turn(self._proc.stdout)

    def _read_turn(self, lines: Iterator[str]) -> Iterator[str]:
        """Yield this turn's text, stopping at its result event.

        If the caller abandons this generator mid-turn — a barge-in, say — the
        remaining events are drained before returning, so the next turn does not
        start reading the tail of the last one.
        """
        finished = False
        try:
            for line in lines:
                event = _decode(line)
                if event is None:
                    continue
                session_id = event.get("session_id")
                if session_id:
                    self.session_id = session_id
                if event.get("type") == "result":
                    finished = True
                    return
                chunk = _text_delta(event)
                if chunk:
                    yield chunk
        finally:
            if not finished:
                self._drain(lines)

    def _drain(self, lines: Iterator[str]) -> None:
        for line in lines:
            event = _decode(line)
            if event is not None and event.get("type") == "result":
                return

    def warm(self) -> None:
        """Pay session initialisation now rather than inside the first question.

        The first turn costs ~2.3 s regardless; this spends it at startup on a
        throwaway exchange so the first thing you actually ask comes back fast.
        """
        try:
            for _ in self.send("Reply with one word: ready."):
                pass
        except (BrokenPipeError, OSError):
            pass

    def close(self) -> None:
        if not self._proc:
            return
        try:
            self._proc.stdin.close()
        except (BrokenPipeError, OSError, ValueError):
            pass
        self._proc.terminate()
        try:
            self._proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            self._proc.kill()
        self._proc = None

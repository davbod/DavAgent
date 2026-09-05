"""Speaking: sentence chunking and the macOS `say` backend.

Text is spoken a sentence at a time so Jarvis starts talking while the model is
still generating, rather than after it finishes.
"""

import re
import subprocess
import threading
from typing import Iterable, Iterator, List, Optional

DEFAULT_VOICE = "Daniel (Enhanced)"

# A sentence ends at .?! followed by whitespace, or at a newline.
_BOUNDARY = re.compile(r"(?<=[.!?])\s+|\n+")
# Below this, hold the fragment back and wait for more — speaking "Yes." then
# "It" then "is." sounds broken.
_MIN_CHARS = 25


def sentences(chunks: Iterable[str], min_chars: int = _MIN_CHARS) -> Iterator[str]:
    """Regroup a stream of arbitrary text chunks into speakable sentences."""
    buffer = ""
    for chunk in chunks:
        buffer += chunk
        # `pos` walks past boundaries we have decided not to split on, so a
        # rejected boundary is never re-examined — otherwise "Yes. " would be
        # tested, merged, and tested again forever.
        pos = 0
        while True:
            match = _BOUNDARY.search(buffer, pos)
            if not match:
                break
            head = buffer[: match.start()]
            if len(head.strip()) < min_chars:
                pos = match.end()  # too short to stand alone: keep accumulating
                continue
            if head.strip():
                yield head.strip()
            buffer = buffer[match.end() :]
            pos = 0
    if buffer.strip():
        yield buffer.strip()


class Speaker:
    """Serialises utterances onto one `say` process at a time, cancellably."""

    def __init__(self, voice: str = DEFAULT_VOICE, rate: Optional[int] = None,
                 command: Optional[List[str]] = None):
        self.voice = voice
        self.rate = rate
        self._command = command
        self._proc: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def _argv(self) -> List[str]:
        if self._command is not None:
            return list(self._command)
        argv = ["say", "-v", self.voice]
        if self.rate:
            argv += ["-r", str(self.rate)]
        return argv

    def say(self, text: str, wait: bool = True) -> None:
        """Speak `text`. Cancels anything currently being said."""
        if not text or not text.strip():
            return
        self.cancel()
        with self._lock:
            # Text goes in on stdin so a leading '-' is never read as a flag.
            self._proc = subprocess.Popen(
                self._argv(), stdin=subprocess.PIPE, text=True
            )
            proc = self._proc
        try:
            proc.communicate(text) if wait else proc.stdin.write(text)
        except (BrokenPipeError, ValueError):
            pass

    def cancel(self) -> None:
        """Stop whatever is being said right now. Safe to call when idle."""
        with self._lock:
            proc, self._proc = self._proc, None
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()

    def is_speaking(self) -> bool:
        with self._lock:
            return self._proc is not None and self._proc.poll() is None

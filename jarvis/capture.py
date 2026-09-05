"""Microphone capture. The mic is open only while a turn is being recorded."""

import sys
from typing import List, Optional

import numpy as np

from . import SAMPLE_RATE

# Below this RMS the take is treated as silence — a key pressed twice by
# accident should not be sent to a model.
SILENCE_RMS = 0.004


def is_silent(audio: np.ndarray, threshold: float = SILENCE_RMS) -> bool:
    if audio is None or len(audio) == 0:
        return True
    return float(np.sqrt(np.mean(np.square(audio)))) < threshold


def trim_silence(audio: np.ndarray, threshold: float = SILENCE_RMS,
                 window: int = 512) -> np.ndarray:
    """Drop leading and trailing silence, keeping a little padding."""
    if audio is None or len(audio) == 0:
        return np.zeros(0, dtype=np.float32)
    frames = max(1, len(audio) // window)
    loud = [
        i for i in range(frames)
        if not is_silent(audio[i * window : (i + 1) * window], threshold)
    ]
    if not loud:
        return np.zeros(0, dtype=np.float32)
    start = max(0, (loud[0] - 2) * window)
    end = min(len(audio), (loud[-1] + 3) * window)
    return audio[start:end]


def drain_keystrokes() -> None:
    """Discard anything typed while Jarvis was busy.

    Without this, Enter presses made during transcription or while Jarvis is
    talking queue up and then satisfy the next two prompts instantly — the
    recording starts and stops with nothing in it, and you get "(nothing
    heard)" for a turn you never took. Observed on the first live run.
    """
    if not sys.stdin.isatty():
        return  # piped input is deliberate; never throw it away
    try:
        import termios

        termios.tcflush(sys.stdin.fileno(), termios.TCIFLUSH)
    except (ImportError, OSError, ValueError):
        pass  # not a real terminal, or no termios — nothing to drain


def record_between_enters(samplerate: int = SAMPLE_RATE,
                          device: Optional[int] = None,
                          prompt: str = "  [Enter] to talk",
                          stop_prompt: str = "  recording — [Enter] to stop") -> np.ndarray:
    """Push-to-talk, terminal edition.

    Deliberately not a global hotkey: that needs macOS Input Monitoring
    permission, which is a poor first thing to ask of a tool that has never
    spoken yet.
    """
    import sounddevice as sd  # imported late: tests must not need portaudio

    drain_keystrokes()
    # EOFError deliberately propagates: Ctrl-D at this prompt means quit, and
    # swallowing it here spun the loop printing "(nothing heard)" forever.
    input(prompt)

    blocks: List[np.ndarray] = []

    def callback(indata, _frames, _time, status):  # noqa: ANN001
        if status:
            pass  # overflows are survivable; a dropped block beats a crash
        blocks.append(indata.copy())

    with sd.InputStream(samplerate=samplerate, channels=1, dtype="float32",
                        device=device, callback=callback):
        try:
            input(stop_prompt)
        except EOFError:
            pass

    if not blocks:
        return np.zeros(0, dtype=np.float32)
    return np.concatenate(blocks, axis=0).flatten().astype(np.float32)

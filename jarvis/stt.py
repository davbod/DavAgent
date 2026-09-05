"""Speech to text, locally. Office audio does not leave this machine."""

import os
from typing import Optional

import numpy as np

from . import SAMPLE_RATE

# small.en is the accuracy/latency sweet spot on Apple silicon. Override with
# JARVIS_WHISPER_MODEL to trade one for the other.
DEFAULT_MODEL = os.environ.get(
    "JARVIS_WHISPER_MODEL", "mlx-community/whisper-small.en-mlx"
)

# Whisper has never heard of most of these, and renders the name as "Jervis"
# without the hint. Kept short — a long prompt biases the whole transcript.
VOCABULARY = "Jarvis. JUMO, Okta, Fleet, Jira, ITSD."


def warm(model: Optional[str] = None) -> None:
    """Load the model before the first utterance.

    The first transcription in a process costs ~1.3 s of model load; every one
    after it is ~0.12 s. Pay that once at startup, not mid-conversation.
    """
    transcribe(np.zeros(SAMPLE_RATE // 10, dtype=np.float32) + 1e-6, model=model)


def transcribe(audio: np.ndarray, model: Optional[str] = None,
               samplerate: int = SAMPLE_RATE) -> str:
    """Transcribe float32 mono PCM. Returns "" for silence."""
    if audio is None or len(audio) == 0:
        return ""
    if samplerate != SAMPLE_RATE:
        raise ValueError(f"expected {SAMPLE_RATE} Hz audio, got {samplerate}")

    import mlx_whisper  # imported late so tests need no model on disk

    result = mlx_whisper.transcribe(
        audio.astype(np.float32),
        path_or_hf_repo=model or DEFAULT_MODEL,
        initial_prompt=VOCABULARY,
        fp16=True,
    )
    return (result.get("text") or "").strip()

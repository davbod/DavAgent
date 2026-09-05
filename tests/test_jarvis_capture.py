import numpy as np

from jarvis.capture import is_silent, trim_silence


def test_silence_is_detected():
    assert is_silent(np.zeros(16000, dtype=np.float32))


def test_empty_audio_is_silent_not_a_crash():
    assert is_silent(np.zeros(0, dtype=np.float32))
    assert is_silent(None)


def test_speech_is_not_silent():
    loud = (np.random.randn(16000) * 0.2).astype(np.float32)
    assert not is_silent(loud)


def test_trim_removes_leading_and_trailing_silence():
    quiet = np.zeros(4000, dtype=np.float32)
    loud = (np.random.randn(8000) * 0.2).astype(np.float32)
    trimmed = trim_silence(np.concatenate([quiet, loud, quiet]))
    assert 0 < len(trimmed) < 16000


def test_trimming_pure_silence_yields_nothing():
    assert len(trim_silence(np.zeros(16000, dtype=np.float32))) == 0


def test_draining_keystrokes_is_a_no_op_off_a_terminal():
    """Piped input is deliberate — tests and --text mode must not lose it."""
    from jarvis.capture import drain_keystrokes

    drain_keystrokes()  # pytest's stdin is not a tty; must not raise

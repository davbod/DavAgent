import numpy as np

from jarvis.brain import EchoBrain
from jarvis.loop import Jarvis


class FakeSpeaker:
    def __init__(self):
        self.said = []
        self.cancelled = 0

    def say(self, text, wait=True):
        self.said.append(text)

    def cancel(self):
        self.cancelled += 1


class AngryBrain:
    def send(self, text):
        yield "Starting to answer this properly. "
        raise KeyboardInterrupt


def test_a_turn_is_spoken():
    speaker = FakeSpeaker()
    jarvis = Jarvis(brain=EchoBrain(), speaker=speaker, echo=False)
    jarvis.respond("what is the time")
    assert speaker.said == ["You said: what is the time"]


def test_secrets_are_muzzled_before_reaching_the_speaker():
    class LeakyBrain:
        def send(self, text):
            yield "Your token: sk-abc123DEF456ghi789xyz is ready to use now."

    speaker = FakeSpeaker()
    Jarvis(brain=LeakyBrain(), speaker=speaker, echo=False).respond("token")
    assert speaker.said, "something should have been said"
    assert "sk-abc123DEF456ghi789xyz" not in " ".join(speaker.said)


def test_barge_in_cancels_the_speaker_without_crashing():
    speaker = FakeSpeaker()
    jarvis = Jarvis(brain=AngryBrain(), speaker=speaker, echo=False)
    jarvis.respond("go on then")
    assert speaker.cancelled >= 1


def test_silence_transcribes_to_nothing():
    jarvis = Jarvis(
        brain=EchoBrain(),
        recorder=lambda: np.zeros(16000, dtype=np.float32),
        transcriber=lambda audio: "should never be called",
        echo=False,
    )
    assert jarvis.listen_once() == ""


def test_speech_reaches_the_transcriber():
    jarvis = Jarvis(
        brain=EchoBrain(),
        recorder=lambda: (np.random.randn(16000) * 0.2).astype(np.float32),
        transcriber=lambda audio: "hello jarvis",
        echo=False,
    )
    assert jarvis.listen_once() == "hello jarvis"


def test_listening_without_a_microphone_is_an_error_not_a_hang():
    try:
        Jarvis(brain=EchoBrain()).listen_once()
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError")


def test_works_with_no_speaker_at_all():
    jarvis = Jarvis(brain=EchoBrain(), speaker=None, echo=False)
    assert jarvis.respond("hello") == "You said: hello"

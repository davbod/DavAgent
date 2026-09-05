import sys
import time

from jarvis.speech import Speaker, sentences


def test_splits_on_sentence_boundaries():
    assert list(sentences(["This is the first sentence. ", "Here is the second one."])) == [
        "This is the first sentence.",
        "Here is the second one.",
    ]


def test_never_splits_mid_word():
    out = list(sentences(["A reasonably long senten", "ce that got chunked oddly."]))
    assert out == ["A reasonably long sentence that got chunked oddly."]


def test_short_fragments_are_held_back():
    # "Yes." alone is too short to speak on its own.
    out = list(sentences(["Yes. ", "That is the whole answer for you."]))
    assert len(out) == 1
    assert out[0].startswith("Yes.")


def test_trailing_text_without_punctuation_is_emitted():
    assert list(sentences(["No trailing full stop here"])) == ["No trailing full stop here"]


def test_empty_stream_yields_nothing():
    assert list(sentences([])) == []


def _sleeper():
    return [sys.executable, "-c", "import sys,time; sys.stdin.read(); time.sleep(30)"]


def test_cancel_kills_in_flight_speech_and_leaves_no_orphan():
    speaker = Speaker(command=_sleeper())
    speaker.say("something long", wait=False)
    assert speaker.is_speaking()
    speaker.cancel()
    time.sleep(0.2)
    assert not speaker.is_speaking()
    assert speaker._proc is None


def test_cancel_when_idle_is_a_no_op():
    Speaker(command=_sleeper()).cancel()


def test_empty_text_spawns_nothing():
    speaker = Speaker(command=_sleeper())
    speaker.say("   ")
    assert not speaker.is_speaking()


def test_voice_and_rate_reach_the_command_line():
    argv = Speaker(voice="Daniel (Enhanced)", rate=200)._argv()
    assert argv[:3] == ["say", "-v", "Daniel (Enhanced)"]
    assert "-r" in argv and "200" in argv

"""ClaudeBrain parses a recorded stream — no CLI, no network."""

import json

from jarvis.brain import ClaudeBrain, EchoBrain

SESSION = "4ebeee03-f955-4c1a-9d0e-000000000000"


def _stream(*events):
    return iter(json.dumps(e) + "\n" for e in events)


def _delta(text):
    return {
        "type": "stream_event",
        "session_id": SESSION,
        "event": {
            "type": "content_block_delta",
            "delta": {"type": "text_delta", "text": text},
        },
    }


def test_deltas_are_yielded_in_order():
    brain = ClaudeBrain()
    out = list(brain._parse(_stream(_delta("hello "), _delta("there"))))
    assert out == ["hello ", "there"]


def test_session_id_is_captured():
    brain = ClaudeBrain()
    list(brain._parse(_stream({"type": "system", "session_id": SESSION})))
    assert brain.session_id == SESSION


def test_session_id_is_reused_on_the_next_turn():
    brain = ClaudeBrain()
    list(brain._parse(_stream(_delta("hi"))))
    argv = brain._argv("next question")
    assert "--resume" in argv
    assert argv[argv.index("--resume") + 1] == SESSION


def test_first_turn_does_not_resume():
    assert "--resume" not in ClaudeBrain()._argv("first question")


def test_malformed_line_is_skipped_not_fatal():
    brain = ClaudeBrain()
    lines = iter(["{not json at all\n", json.dumps(_delta("survived")) + "\n"])
    assert list(brain._parse(lines)) == ["survived"]


def test_result_is_not_spoken_when_deltas_arrived():
    """The reply must never be said twice."""
    brain = ClaudeBrain()
    out = list(brain._parse(_stream(
        _delta("hello there"),
        {"type": "result", "session_id": SESSION, "result": "hello there"},
    )))
    assert out == ["hello there"]


def test_result_is_the_fallback_when_no_deltas_arrived():
    brain = ClaudeBrain()
    out = list(brain._parse(_stream(
        {"type": "result", "session_id": SESSION, "result": "fallback reply"},
    )))
    assert out == ["fallback reply"]


def test_non_text_deltas_are_ignored():
    brain = ClaudeBrain()
    out = list(brain._parse(_stream({
        "type": "stream_event",
        "event": {"type": "content_block_delta",
                  "delta": {"type": "thinking_delta", "thinking": "hmm"}},
    })))
    assert out == []


def test_blank_lines_are_ignored():
    assert list(ClaudeBrain()._parse(iter(["\n", "  \n"]))) == []


def test_voice_system_prompt_is_passed():
    argv = ClaudeBrain()._argv("q")
    assert "--append-system-prompt" in argv
    prompt = argv[argv.index("--append-system-prompt") + 1]
    assert "spoken" in prompt.lower()


def test_echo_brain_repeats_and_records():
    brain = EchoBrain()
    assert "".join(brain.send("ping")) == "You said: ping"
    assert brain.heard == ["ping"]


def test_conversational_brain_denies_every_tool():
    """A denylist leaked in testing; only the wildcard held."""
    argv = ClaudeBrain()._argv("q")
    assert "--disallowed-tools" in argv
    assert argv[argv.index("--disallowed-tools") + 1] == "*"
    assert "--strict-mcp-config" in argv


def test_tools_can_be_unlocked_deliberately():
    argv = ClaudeBrain(conversational=False)._argv("q")
    assert "--disallowed-tools" not in argv


def test_effort_is_low_for_conversation():
    argv = ClaudeBrain()._argv("q")
    assert argv[argv.index("--effort") + 1] == "low"


# --- persistent brain: one process, many turns -------------------------------

from jarvis.brain import PersistentClaudeBrain


def _line(obj):
    return json.dumps(obj) + "\n"


def _result():
    return _line({"type": "result", "subtype": "success", "session_id": SESSION})


def test_a_turn_stops_at_its_result_event():
    brain = PersistentClaudeBrain()
    lines = iter([_line(_delta("one")), _result(), _line(_delta("NEXT TURN"))])
    assert list(brain._read_turn(lines)) == ["one"]


def test_the_next_turn_is_not_read_as_part_of_this_one():
    brain = PersistentClaudeBrain()
    lines = iter([_line(_delta("one")), _result(), _line(_delta("two")), _result()])
    assert list(brain._read_turn(lines)) == ["one"]
    assert list(brain._read_turn(lines)) == ["two"]


def test_abandoning_a_turn_drains_it_to_the_boundary():
    """Barge-in: the caller stops listening, but the stream must stay aligned."""
    brain = PersistentClaudeBrain()
    lines = iter([
        _line(_delta("start")), _line(_delta("more")), _result(),
        _line(_delta("next turn")), _result(),
    ])
    turn = brain._read_turn(lines)
    assert next(turn) == "start"
    turn.close()
    assert list(brain._read_turn(lines)) == ["next turn"]


def test_session_id_is_tracked_across_turns():
    brain = PersistentClaudeBrain()
    list(brain._read_turn(iter([_line(_delta("hi")), _result()])))
    assert brain.session_id == SESSION


def test_malformed_line_does_not_break_a_turn():
    brain = PersistentClaudeBrain()
    lines = iter(["{ broken\n", _line(_delta("survived")), _result()])
    assert list(brain._read_turn(lines)) == ["survived"]


def test_persistent_brain_also_denies_every_tool():
    argv = PersistentClaudeBrain()._argv()
    assert argv[argv.index("--disallowed-tools") + 1] == "*"
    assert "--strict-mcp-config" in argv
    assert "--input-format" in argv


def test_close_is_safe_when_never_started():
    PersistentClaudeBrain().close()

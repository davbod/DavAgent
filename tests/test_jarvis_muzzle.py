"""The muzzle is a security control, so these are security tests."""

from jarvis.muzzle import scrub


def test_labelled_secret_never_survives():
    out = scrub("The token: sk-abc123DEF456ghi789 is set")
    assert "sk-abc123DEF456ghi789" not in out
    assert "redacted" in out


def test_long_opaque_token_is_redacted():
    secret = "A" * 40
    assert secret not in scrub(f"use {secret} to authenticate")


def test_long_hex_is_redacted():
    digest = "deadbeef" * 4
    assert digest not in scrub(f"the hash is {digest}")


def test_password_assignment_is_redacted():
    assert "hunter2" not in scrub("password=hunter2")


def test_urls_are_summarised_not_spelled_out():
    out = scrub("See https://jumo.world/very/long/path for detail")
    assert "https" not in out
    assert "link" in out


def test_paths_are_summarised():
    out = scrub("It is in /Users/davidbodmer/secrets/file.txt somewhere")
    assert "davidbodmer" not in out
    assert "file path" in out


def test_emails_are_redacted_by_default():
    out = scrub("Mail someone@jumo.world about it")
    assert "@" not in out
    assert "email address" in out


def test_emails_can_be_allowed_through():
    assert "someone@jumo.world" in scrub("Mail someone@jumo.world", redact_emails=False)


def test_code_fences_become_a_summary():
    out = scrub("Try this:\n```python\nimport os\nos.remove('/')\n```\nDone")
    assert "import os" not in out
    assert "some code" in out


def test_markdown_syntax_is_stripped():
    out = scrub("**bold** and `code` and # heading")
    assert "*" not in out and "`" not in out and "#" not in out


def test_plain_speech_is_left_alone():
    assert scrub("Two tickets need attention today.") == "Two tickets need attention today."


def test_empty_input_is_safe():
    assert scrub("") == ""
    assert scrub(None) == ""


def test_tool_call_markup_is_never_spoken():
    """Observed live: with all tools denied, the model writes tool syntax as text."""
    leaked = '<parameter name="description">Run whoami</parameter></invoke davidbodmer'
    out = scrub(leaked)
    assert "<" not in out and ">" not in out
    assert "parameter" not in out and "invoke" not in out


def test_partial_streamed_tag_is_stripped():
    assert "<" not in scrub("Here we go <function_calls")


def test_angle_brackets_in_ordinary_speech_survive_readably():
    # Not a tag, so nothing should vanish mid-sentence.
    assert "five" in scrub("It took five minutes")

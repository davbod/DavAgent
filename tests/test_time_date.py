import re

from tools import time_date


def test_get_time_date_matches_expected_format():
    result = time_date.get_time_date()
    assert result.startswith("Current date and time: ")
    body = result[len("Current date and time: "):]
    # e.g. "2026-08-14 21:47:03 PDT" — trailing timezone abbrev is best-effort,
    # so only require the date/time portion to match strictly.
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", body)

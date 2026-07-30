from datetime import datetime


def get_time_date():
    """Returns the current local date and time."""
    print("\n   [Executing] -> Getting current date/time...")
    now = datetime.now().astimezone()
    return f"Current date and time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}"


TOOLS = {
    "get_time_date": get_time_date,
}

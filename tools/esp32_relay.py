def trigger_esp32_relay(device_ip: str, action: str):
    """Simulates hitting a local endpoint to trigger hardware."""
    print(f"\n   [Executing] -> Sending '{action}' to ESP32 at {device_ip}...")
    # In a real setup, you would execute the network request:
    # return requests.get(f"http://{device_ip}/{action}").text
    return f"Success: {device_ip} relay set to {action}"


# Placeholder hardware tool — not needed for this project, so it is not exported
# to AVAILABLE_TOOLS. Re-add it to TOOLS below to enable it.
TOOLS = {}

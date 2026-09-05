"""python -m jarvis — talk to Jarvis."""

import argparse
import sys

from .brain import DEFAULT_MODEL, ClaudeBrain, EchoBrain, PersistentClaudeBrain
from .loop import Jarvis
from .speech import DEFAULT_VOICE, Speaker


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="jarvis", description="Talk to Jarvis.")
    parser.add_argument("--text", action="store_true",
                        help="type instead of talking (no microphone needed)")
    parser.add_argument("--echo-brain", action="store_true",
                        help="repeat back instead of calling a model")
    parser.add_argument("--one-shot-brain", action="store_true",
                        help="spawn a fresh session per turn (slower; a fallback)")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--rate", type=int, default=None, help="words per minute")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--device", type=int, default=None, help="input device index")
    parser.add_argument("--silent", action="store_true", help="print, do not speak")
    parser.add_argument("--list-devices", action="store_true")
    args = parser.parse_args(argv)

    if args.list_devices:
        import sounddevice as sd

        for index, device in enumerate(sd.query_devices()):
            if device["max_input_channels"] > 0:
                print(f"{index}: {device['name']}")
        return 0

    if args.echo_brain:
        brain = EchoBrain()
    elif args.one_shot_brain:
        brain = ClaudeBrain(model=args.model)
    else:
        brain = PersistentClaudeBrain(model=args.model)
    speaker = None if args.silent else Speaker(voice=args.voice, rate=args.rate)

    recorder = transcriber = None
    if not args.text:
        from .capture import record_between_enters
        from .stt import transcribe, warm

        print("Waking Jarvis up...", flush=True)
        warm()  # pay the whisper model load now, not inside the first turn
        if hasattr(brain, "warm"):
            brain.warm()  # and the session init too — worth ~2.3s on turn one

        def recorder():  # noqa: F811
            return record_between_enters(device=args.device)

        transcriber = transcribe

    jarvis = Jarvis(brain=brain, speaker=speaker,
                    recorder=recorder, transcriber=transcriber)
    if args.text:
        jarvis.run_text()
    else:
        jarvis.run_voice()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""The conversation loop: listen, think, speak, repeat."""

from typing import Callable, Iterator, Optional

from .brain import Brain
from .muzzle import scrub
from .speech import Speaker, sentences


class Jarvis:
    """Wires a brain to ears and a mouth.

    Every collaborator is injected so the loop can be exercised without a
    microphone, a model, or a speech synthesiser.
    """

    def __init__(
        self,
        brain: Brain,
        speaker: Optional[Speaker] = None,
        recorder: Optional[Callable] = None,
        transcriber: Optional[Callable] = None,
        muzzle: Callable[[str], str] = scrub,
        echo: bool = True,
    ):
        self.brain = brain
        self.speaker = speaker
        self.recorder = recorder
        self.transcriber = transcriber
        self.muzzle = muzzle
        self.echo = echo

    def respond(self, text: str) -> str:
        """Run one turn. Returns everything that was actually spoken."""
        spoken = []
        try:
            for sentence in sentences(self.brain.send(text)):
                safe = self.muzzle(sentence)
                if not safe:
                    continue
                spoken.append(safe)
                if self.echo:
                    print(f"  jarvis: {safe}", flush=True)
                if self.speaker:
                    self.speaker.say(safe)
        except KeyboardInterrupt:
            # Barge-in, P1 edition: Ctrl-C stops the mouth, not the program.
            if self.speaker:
                self.speaker.cancel()
            print("  (stopped)", flush=True)
        return " ".join(spoken)

    def listen_once(self) -> str:
        """Record one utterance and transcribe it. Returns "" for silence."""
        if not (self.recorder and self.transcriber):
            raise RuntimeError("no recorder/transcriber configured")
        audio = self.recorder()
        from .capture import is_silent, trim_silence

        audio = trim_silence(audio)
        if is_silent(audio):
            return ""
        return self.transcriber(audio)

    def run_voice(self) -> None:
        print("Jarvis is listening. Ctrl-C stops him talking, Ctrl-D quits.\n")
        consecutive_silence = 0
        while True:
            try:
                heard = self.listen_once()
            except (EOFError, KeyboardInterrupt):
                break
            if not heard:
                consecutive_silence += 1
                if consecutive_silence >= 3:
                    print("  (nothing heard — Ctrl-D to quit)", flush=True)
                else:
                    print("  (nothing heard)", flush=True)
                continue
            consecutive_silence = 0
            print(f"  you: {heard}", flush=True)
            self.respond(heard)
        self._goodbye()

    def run_text(self) -> None:
        print("Jarvis, typed. Ctrl-D quits.\n")
        while True:
            try:
                heard = input("  you: ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if heard:
                self.respond(heard)
        self._goodbye()

    def _goodbye(self) -> None:
        if self.speaker:
            self.speaker.cancel()
        close = getattr(self.brain, "close", None)
        if close:
            close()
        print("\nJarvis out.")

# 002 — Jarvis (voice conversation module)

**Status:** approved (recommended defaults taken) — phase 1 implemented 2026-09-02
**Date:** 2026-09-01

> Divergences from this spec are recorded in `DEVLOG.md` (2026-09-02), not patched
> back into it. The headline ones: Python 3.11 not 3.14, mlx-whisper not whisper.cpp,
> terminal push-to-talk not a global hotkey, and an enumerated tool denylist that
> leaked and had to become a wildcard.

## Problem

Voice on this Mac is currently one-way and unsolicited. A Claude Code Stop hook
(`~/.claude/hooks/speak.sh`) read a spoken summary after *every* turn. It was
unwired on 2026-09-01 because narration you did not ask for is noise, not
assistance. Speech is now on-demand only, via `~/.claude/hooks/speak-now.sh`.

What is actually wanted is a conversation: talk to the agent, hear it answer,
and have it stay quiet when it is not being addressed.

The input half does not exist at all. Verified on this machine today: no STT
engine, no whisper build, no mic-capture library (`sounddevice`, `pyaudio`,
`numpy` all absent), and no wake or push-to-talk path. Ollama is installed but
its server is not even running.

## Goals

1. Speak to the agent hands-free; hear the reply aloud.
2. Audio never leaves the Mac. Transcription is local; only the resulting text
   reaches a model — the same exposure as typing today.
3. Silent unless addressed. Mic closed by default.
4. Pluggable brain: the local Ollama loop, or Claude.
5. Barge-in — talking over Jarvis stops it mid-sentence.
6. Never speak secrets, credentials, or customer data aloud.

## Non-goals

- Wake word in v1 (deferred to phase 3, opt-in).
- Neural TTS. macOS `say` is good enough to start and costs nothing.
- Speaker identification or multi-user support.
- Operating during Zoom calls — Jarvis mutes instead.
- Replacing Claude Code for real IT work. Jarvis is a front-end, not a rival agent.

## Design

New package `jarvis/` inside DavAgent:

| File | Responsibility |
|------|----------------|
| `capture.py` | Mic → 16 kHz mono PCM via `sounddevice`. Push-to-talk gate, silence trim. |
| `stt.py` | `transcribe(pcm) -> str`. whisper.cpp with Metal on the M5, `small.en`. |
| `brain.py` | `Brain` protocol: `send(text) -> Iterator[str]`, yielding text chunks. |
| `speech.py` | Sentence chunker → queue → `say` subprocess. `cancel()` kills in-flight audio. |
| `muzzle.py` | Redaction gate every chunk passes through before it can be spoken. |
| `loop.py` | State machine and the hotkey wiring. |

Two brains behind one protocol:

- `OllamaBrain` — wraps DavAgent's existing loop. Fully offline.
- `ClaudeBrain` — subprocess against the installed CLI (verified present,
  v2.1.236):
  `claude -p --output-format stream-json --include-partial-messages --resume <session-id>`
  Parses the NDJSON stream, yields assistant text deltas as they arrive, and
  persists the session id so each utterance continues the same conversation
  rather than starting cold.

State machine: `IDLE → LISTENING → TRANSCRIBING → THINKING → SPEAKING → IDLE`,
with a barge-in edge `SPEAKING → LISTENING` that cancels playback.

Per utterance: hotkey down → capture → hotkey up → whisper → `brain.send()` →
split output at sentence boundaries → speech queue → `say`. A fresh hotkey press
at any point cancels speech and starts a new capture.

Latency budget on the M5: whisper `small.en` over ~5 s of audio ≈ 0.3–0.6 s,
first Claude token ≈ 0.8–1.5 s at low effort, TTS begins on the first complete
sentence rather than waiting for the full answer. Target: speaking within ~2 s
of releasing the key.

Model: `claude-opus-5` at `effort: low` for conversational turns, escalating to
`high` only when Jarvis is asked to actually do work.

Runtime: a venv on `python3.14` (Homebrew). The system interpreter is 3.9.6 and
is too old for the current SDKs — do not build against it. This is the same
3.9-vs-modern trap that already blocks `jira-assets.py` in the JUMO workspace.

Phasing:

- **P0 — done.** On-demand speech (`speak-now.sh`), automatic narration off.
- **P1.** Push-to-talk one-shot: hotkey → whisper → `ClaudeBrain` → `say`. Only
  new dependencies are whisper and `sounddevice`.
- **P2.** Daemon with streaming output, barge-in, and `OllamaBrain`. Move to the
  Claude Agent SDK (`code.claude.com/docs/en/agent-sdk`) here if the CLI's
  streaming proves too coarse.
- **P3.** Wake word "Jarvis", opt-in behind its own toggle.
- **P4.** Workspace duties — spoken ticket triage, Fleet/Okta lookups. Needs an
  IT ticket first; see Security notes.

## Test plan

- `capture`: silence yields empty PCM and no crash.
- `stt`: a fixture wav transcribes to known text, whisper binary stubbed.
- `brain`: `ClaudeBrain` parses a recorded stream-json fixture into ordered chunks.
- `brain`: a malformed NDJSON line is skipped, not fatal.
- `brain`: session id round-trips — the second `send()` resumes the first's id.
- `speech`: chunker splits on sentence boundaries, never mid-word.
- `speech`: `cancel()` kills in-flight `say` and leaves no orphan pid.
- `muzzle`: token-, key-, and password-shaped strings never reach TTS.
- `muzzle`: paths and URLs are summarised, not spelled out character by character.
- `loop`: barge-in during SPEAKING transitions to LISTENING and cancels audio.

All run with no network and no live Ollama; `whisper` and `say` are stubbed.

## Security notes

- **Audio stays local.** whisper.cpp runs on the machine. No cloud STT, ever —
  office audio is not ours to upload.
- **Transcripts are not persisted.** In-memory for the session only.
- **Text does reach Claude** under `ClaudeBrain` — identical exposure to typing
  into Claude Code. Do not dictate credentials or customer data.
- **Mic closed unless the key is held.** No always-on capture in v1. The wake
  word in P3 is a separate, explicit opt-in, not a default.
- **`muzzle.py` is a hard gate, not a nicety.** JUMO is a regulated financial
  platform. Anything spoken aloud in an open-plan office is disclosed to
  everyone within earshot — a far weaker boundary than a screen. No tokens,
  keys, or PII are ever voiced.
- **Auto-mute during Zoom meetings** so Jarvis never speaks into a live call.
- **Jira scope.** DavAgent is a personal project, so P1–P3 need no ticket. The
  moment Jarvis is pointed at JUMO systems — Fleet, Okta, Jira, tickets read
  aloud (P4) — that is JUMO work and needs an IT ticket opened first.

## Open questions — for the lead

1. **Push-to-talk key.** Recommend right-Option, held. Alternative: a menu-bar
   toggle, which avoids needing Input Monitoring permission.
2. **Default brain.** Recommend `ClaudeBrain`; Ollama is not currently running.
3. **Whisper model size.** Recommend `small.en`. `medium.en` if South African
   accent accuracy disappoints — roughly 3x slower.
4. **Jarvis's voice.** Recommend `Daniel (Enhanced)` (en_GB), leaving
   `Serena (Premium)` to Claude Code, so you can hear which one is talking.
5. **Home.** Recommend a module inside DavAgent, reusing its memory, library,
   and spec process, rather than a standalone repo.

## Risks

- whisper.cpp may need toolchain work on the M5; fallback is `mlx-whisper`.
- `say` is robotic. If it grates, `speech.py`'s backend is one function to swap.
- Hotkey capture needs macOS Accessibility / Input Monitoring permission; the
  menu-bar toggle sidesteps this.
- **Self-triggering.** With speakers rather than headphones, an open mic hears
  Jarvis and barges in on itself. Mitigate by gating the mic while speaking.

## Rejected alternatives

- **macOS Dictation as STT.** No programmatic API; cannot be driven by a daemon.
- **Cloud STT (Whisper API, Deepgram).** Sends office audio off the machine.
  Non-starter here.
- **Doing the input side inside a Claude Code hook.** No hook can inject user
  input into a session — hooks observe and intercept, they do not originate
  turns. Voice input is therefore impossible in-process; Jarvis must be a
  separate program. This is the constraint that shapes the whole design.
- **Claude Agent SDK for P1.** The right eventual harness, but it needs a new
  Python runtime and package installed before anything can speak at all. The CLI
  subprocess proves the loop end-to-end first.
- **Managed Agents / the API tool runner.** Wrong tier. Jarvis needs the local
  filesystem and the workspace, not a hosted sandbox.

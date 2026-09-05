# DavAgent Dev Log

An engineering diary: what changed, **why**, what was rejected, and what we learned.
Code and commits record *what* the project does; this file records the thinking that
produced it, including the dead ends — those are usually the expensive part to rediscover.

Entries are newest-first. The idea below is the stable part; everything under it is history.

---

## The Idea

DavAgent is a **low-profile, local, moddable agent assistant**. A person runs it on their
own laptop against their own model, and it can actually do things — read and write files,
remember, research, look things up — without any of that leaving the machine.

Four principles drive most decisions here. When a choice is hard, these are the tiebreakers:

1. **Local and private by default.** The model is local (Ollama). Data stays on disk in
   plain files. Reaching for a cloud service should feel like a deliberate exception, not
   the default path.
2. **Small dependency budget.** `requests` and nothing else, so far. Every new dependency
   must earn its place against the stdlib. This has already cost us capability (see the
   HTML extraction note, 2026-08-14) and that was judged the right trade.
3. **Moddable by a hobbyist.** Drop a `.py` file in `tools/`, give the function type hints
   and a docstring, export `TOOLS`. The JSON schema the model needs is generated from that.
   Nobody should ever hand-write a tool schema, and nobody should have to read the whole
   codebase to add a capability.
4. **Readable over clever.** This is a project someone should be able to sit down and
   understand in an evening.

**Working method (from 2026-08-15):** spec-driven. Each segment gets a lightweight spec in
`docs/specs/` that the project lead approves *before* implementation, and design/review work
is fanned out across parallel agents rather than done in a single pass. Tests accompany every
change and must run with no network and no live Ollama.

---

## 2026-09-02 (later) — Persistent session, and a measurement that lied

Phase 2's first piece landed: `PersistentClaudeBrain` holds one `claude -p` process open
and feeds each utterance in over stdin as a turn, instead of spawning a session per turn.
Each turn is delimited by a `result` event, which is what makes reading one turn at a time
tractable.

**Measured, fairly, same questions back to back:**

| Brain | First word per turn | Mean |
|---|---|---|
| One-shot, session per turn | 2.62 / 3.92 / 3.30 / 2.54 s | 3.09 s |
| Persistent, warm | 2.06 / 1.94 / 1.66 / 1.79 s | 1.86 s |

A 40% cut, about 1.2 s a turn. Worth having, and the remaining 1.9 s is the floor for a
cloud round trip from Cape Town — not something more tuning will fix.

**The lesson is in how nearly this went wrong.** The first probe reported 0.16-0.69 s for
warm turns, four times better than the real figure. It was measuring an artefact: the
probe broke out of reading as soon as it saw the first token and immediately wrote the
next question, so each request was queued while the previous turn was still streaming.
The model had the next question in hand before it was asked. Pipelined, not fast.

Nothing about the probe looked wrong, and the number it produced was the number we wanted
to see, which is exactly when a measurement deserves the most suspicion. Caught only by
re-running the same questions through the real class and getting 1.86 s. **Benchmark the
thing you ship, not a sketch of it** — and be most sceptical of a result that flatters
the change you just made.

`warm()` costs ~3.9 s at startup and buys the first real question the warm figure rather
than the cold one. The one-shot brain stays as `--one-shot-brain`, and both now share the
same event-parsing helpers so they cannot drift apart.

---

## 2026-09-02 — Jarvis phase 1: it listens, thinks and talks back

Built the voice front-end from spec 002. Phase 1 works end to end: speech in, spoken
answer out, conversation carried across utterances. What follows is what the spec got
wrong, because that is the expensive part to rediscover.

**Two principles took a knock, deliberately.** Principle 2 says `requests` and nothing
else; Jarvis adds `sounddevice`, `numpy` and `mlx-whisper`. Principle 1 says local by
default; the default brain is Claude, in the cloud. Both were judged worth it — there is
no stdlib path to a microphone or a speech model, and the local brain is still there
behind the same interface. The blast radius is contained: the dependencies live in
`.venv-jarvis` and `requirements-jarvis.txt`, so DavAgent core still installs on
`requests` alone and its tests still pass untouched (121 of them, then 124).

**The denylist leaked, and that is the finding worth remembering.** Phase 1 is meant to
be conversation only — touching a real system is phase 4 and needs a ticket first. The
first attempt enumerated the tools to deny: Bash, Edit, Write, Read and so on. Asked to
run `whoami`, Jarvis reached the same shell through a tool that was not on the list and
returned the answer. Denying the things you can think of is not a boundary. Only
`--disallowed-tools "*"` held. Allow capability back explicitly, per phase — never
subtract it.

Worth knowing how that leak was found: not by reading the code, but by asking Jarvis to
do the forbidden thing and watching. The first end-to-end run had already shown the same
shape — asked casually how many tickets were waiting, it went and queried Jira for real,
because the CLI brain inherits the full toolset by default. Impressive, and exactly what
the spec said must not happen yet.

**Denying every tool has a side effect.** With nothing to call, the model sometimes writes
tool-call syntax into its visible text instead — `<parameter name=...>` and friends — which
the speech synthesiser then reads out character by character. Fixed in two places: the
system prompt now states plainly that there are no tools, and the muzzle strips tag-shaped
text before anything can be spoken. Belt and braces, because the prompt is advice and the
muzzle is a gate.

**Latency, measured rather than guessed.** The spec estimated whisper at 0.3–0.6 s and
first token at 0.8–1.5 s, so about 2 s to first word. Reality on the M5: transcription is
0.11 s once warm — five times better than estimated — but the first token takes 2.5–3.0 s,
so the real figure is nearer 2.6 s. The model load costs 1.45 s on first use, now paid at
startup instead of inside the first sentence.

The latency is not process startup: the CLI binary itself launches in 0.06 s. It is
session initialisation, once per turn. Stripping settings to avoid it made things
dramatically worse — 15.5 s versus 2.0 s, presumably losing a warm prompt cache — so the
fix is not less context but fewer starts. Phase 2 should hold one CLI process open and
feed it utterances via `--input-format stream-json`.

**Three departures from the spec, all for the same reason — get to a working loop sooner.**
Python 3.11 rather than 3.14, because wheels exist for it. `mlx-whisper` rather than
whisper.cpp, because it is a pip install rather than a toolchain, and at 0.11 s there is
nothing to gain by building C++. Terminal push-to-talk rather than a global hotkey,
because a tool that has never spoken yet has not earned macOS Input Monitoring permission.

Whisper heard the name as "Jervis" until given a vocabulary hint. It now hears "Jarvis".

Everything up to the microphone was verified by having `say` generate the audio and
feeding that back through transcription — a genuinely useful trick for testing STT with
no mic, no permission prompt, and a known-correct transcript to compare against.

**Then the live run, which found two bugs the synthetic one structurally could not.**
Both exchanges worked — it heard a South African accent correctly first time, unprompted
— but the terminal filled with phantom turns: prompts printing two to a line, then
"(nothing heard)" for a turn nobody took.

The cause was buffered stdin. Enter presses made while Jarvis was transcribing or talking
sat in the terminal buffer and then satisfied the next two prompts instantly, opening and
closing a recording with nothing in it. Obvious in hindsight, invisible to every test we
had: piped stdin never queues behind a slow consumer the way a human at a keyboard does.
Fixed by draining the terminal buffer before prompting — and only when stdin is a real
tty, because piped input is deliberate and must never be thrown away.

The second bug was in the same area. `record_between_enters` caught `EOFError` and
returned silence, so Ctrl-D never reached the loop that knows how to quit: it printed
"(nothing heard)" forever and had to be killed with Ctrl-C. The fix was to stop catching
it. A handler that converts "the user is done" into "the user said nothing" is worse than
no handler at all.

The lesson worth keeping: the synthetic harness proved the pipeline, but every defect it
missed lived in the boundary between the program and a human at a terminal — timing,
buffering, and the difference between silence and EOF. Test the pipeline synthetically;
test the interaction with a person.

---

## 2026-08-17 (later) — Correction: the workflow did finish, ~50 hours in

**Correcting the entry below, which is wrong.** I checked the workflow, found no completion,
diagnosed it as dead, wrote it up as a failure, and committed that. Minutes later it completed
— after a **50-hour** wall-clock run. Final tally: 11 agents, 5 completed, 6 errored (two
research agents stalled through all 6 retry attempts, and all three proposal agents died).

I'm leaving the failure post-mortem below intact rather than rewriting it, because its process
lessons still hold and because a devlog that quietly edits out its author's wrong calls is worth
less than one that doesn't. But its headline conclusion — "no spec was produced" — was wrong.

**What it actually produced.** A strong spec, now written up as `docs/specs/001-web-search.md`
(status: awaiting approval). The synthesis agent worked around its dead upstream: with all three
proposals empty, the judges returned BLOCKED, so it read the repo and the salvaged research
notes I had committed that morning and did the analysis itself. The salvage work fed the run
that made the salvage look premature.

**Three findings that matter more than the spec:**

1. **The tide mystery is solved, and it vindicates the whole segment.** A real search returns
   `.../Cape-Town-South-Africa/tides/latest`. The agent's 404'd guess was `.../tides` — **wrong
   by one path segment**. No amount of permutation reaches that. Discovery really was the binding
   constraint, not extraction.

2. **A live SSRF hole in code I wrote and committed.** `tools/web.py` validates only the URL
   scheme, so `fetch_url` can reach `http://localhost:11434/api/*` — the user's own Ollama
   control plane, which can delete models — plus `169.254.169.254` and all RFC1918 space, and
   `requests` follows redirects with no revalidation. Latent while the model guessed its own
   URLs; reachable the moment a third party supplies them. Flagged to the lead, not silently
   patched.

3. **A prompt-injection amplification path through the architecture.** `main.py` appends tool
   output with no trust separation *and* rebuilds the system prompt from `memory.md` every turn,
   while `save_memory` is model-callable without confirmation. One injected `save_memory` call
   becomes a persistent system-prompt implant surviving restart. That is an emergent consequence
   of two individually reasonable choices — proactive memory saves, and refreshing memory each
   turn — and neither looked risky on its own.

**Revised process lessons.** The one below ("long fan-outs are fragile") needs amending: the
run was not fragile so much as *unbounded*. It burned 859k subagent tokens over 50 hours with no
wall-clock ceiling, and I had no way to tell "stalled" from "still thinking" — which is why I
called it dead. Next time: cap the run, and treat absence of a result as unknown rather than
failure. Two of my three original lessons survive unchanged, and the best one is confirmed
twice over — **the agents told to go and measure produced everything durable; the agents asked
to assess produced nothing recoverable.**

---

## 2026-08-17 — The design workflow failed; what we kept, and where to resume

> **Superseded in its conclusion by the entry above** — the workflow completed shortly after
> this was written. The diagnosis and process lessons here still stand; "no spec was produced"
> does not.

**What happened.** The 11-agent workflow launched on 2026-08-15 to design the web-search
segment **did not complete**. Of the agents that ran, exactly two reached a normal end of turn:
the repo-conformance researcher and the security judge. Every other agent died mid-tool-call.
Two of the research agents were retried roughly six times each and never finished. The final
synthesis step never ran, so **no spec was produced**.

**Diagnosis (partial, honest).** Two contributing causes are visible in the transcripts:

1. At least one tool call came back `Permission for this tool use was denied`. Agents running
   in the background have nobody to answer a permission prompt, so work that needs approval
   stalls rather than proceeding.
2. The agents were mid-flight when the session went idle, and did not survive to be resumed.
   Workflow resume is same-session only, so the partial state could not simply be continued.

I have not proven these are the *whole* story, and I'm recording that uncertainty rather than
tidying it away.

**What this cost, and what we kept.** The run consumed a lot of tokens for one usable research
document. Before stopping, the salvageable output was extracted from the raw agent transcripts
into `.workflow-research/001-web-search/` (gitignored) and the substance distilled into
`docs/specs/001-web-search-notes.md` (committed, with a provenance table — measured findings are
marked separately from unverified claims).

The genuinely valuable survivor: an agent **empirically probed** keyless search endpoints instead
of theorising. DuckDuckGo's HTML endpoint answers `HTTP 202` with a captcha when it thinks you're
a bot and self-clears in about three minutes; `startpage` returns `200` with a JS-only body —
failing exactly the way `weathersa.co.za` did in the tide test; `ecosia` and `yep` return `403`.
That is worth more than any of the lost prose.

**Lessons for how we run workflows.**

- **Long autonomous fan-outs are fragile across an idle session.** For a hobby-scale project,
  a smaller workflow that finishes inside one sitting beats a thorough one that dies at 80%.
- **Give background agents no reason to need permission.** Anything requiring approval should be
  done in the main session, not inside a background fan-out.
- **Journal the intermediate results, not just the final return.** The one completed research
  doc was recoverable only because it happened to be journaled; the rest had to be reconstructed
  from raw transcripts, and mostly couldn't be.
- **Measurement beat argument.** The one agent that made real HTTP requests produced the only
  durable finding. Bias future research prompts toward "go and test it" over "assess the options".

**Where to resume.** First: verify or kill the unverified lead that Ollama offers a native web
search API — it would change the backend decision, and Ollama is already a hard dependency.
Then finish the keyed-backend comparison and write the spec. Nothing is blocked; the tree is
clean and the baseline is committed.

---

## 2026-08-15 — Process: spec-driven development, and this log

**What changed.** Introduced this dev log, a `docs/specs/` directory, and a standing working
method: research and design each segment via parallel multi-agent workflows, write a
lightweight spec, get lead approval, *then* implement against it with tests.

**Why.** The work up to this point was good but improvised — decisions were made mid-flow and
only survived in the transcript. Two things were being lost: the *reasoning* behind a design
(why the library is separate from memory, why stdlib HTML parsing over BeautifulSoup), and the
*negative* results (what we tried that didn't work). The tide experiment on 2026-08-14 is the
clearest example: it produced the single most useful finding so far, and none of it lived
anywhere durable.

**Also.** Committed the accumulated work as three logical commits on `chore/pre-spec-baseline`
so the process starts from a clean, described tree rather than a pile of unstaged changes.

---

## 2026-08-14 — The Cape Town tide experiment (the useful failure)

**What we did.** Ran DavAgent end-to-end against a real research task — "what time is high tide
tomorrow in Cape Town" — and watched the tool-call trace live, with the intent of killing it if
it looped or hallucinated.

**What happened.** Four fetches across two domains, then a clean surrender:

| # | URL | Result |
|---|---|---|
| 1 | `tide-forecast.com/locations/Cape-Town-South-Africa/tides` | HTTP 404 |
| 2 | `tide-forecast.com/locations/Cape-Town/tides` | HTTP 404 |
| 3 | `weathersa.co.za/tides/cape-town` | HTTP 200, empty SPA shell |
| 4 | `weathersa.co.za/tides/capetown` | HTTP 200, empty SPA shell |

It then told the user it couldn't retrieve real data and suggested checking a browser.

**What we learned — three separate things, worth keeping distinct:**

1. **The model's judgment was fine.** Faced with four failures it declined to invent a
   high-tide time. For a tool-using local model that is exactly the right failure mode, and
   it's worth noting because it's the part we didn't have to fix.

2. **A real bug in our own code.** `weathersa.co.za` returned `Content-Type: text/HTML` —
   capital HTML. `fetch_url`'s check was `"html" in content_type`, case-sensitive, so it missed,
   fell through to the plain-text branch, and dumped raw markup and Cloudflare JS into the
   model's context instead of extracting text or reporting that the page had none. We fed the
   model garbage and it reasonably went and guessed another URL. Fixed by lowercasing before
   the check, with two regression tests.

3. **The actual capability gap.** DavAgent cannot *discover* a URL — only guess one from what
   the model remembers. Pages 1 and 2 were the same guess with different slug spellings. This
   is structural, not a tuning problem, and is why web search is the next segment.

**Secondary finding, not yet addressed.** Nothing in the agent loop caps retries or notices
near-identical repeated calls. The model self-limited this time; it isn't guaranteed to.
Logged as a candidate segment.

**Method note.** Piping a query into `main.py` and watching a filtered log proved a genuinely
good way to evaluate agent behaviour. Worth keeping as the standard way to test changes to the
loop — unit tests can't catch "it guessed four URLs and gave up".

---

## 2026-08-14 — Memory vs. Library: splitting continuity from knowledge

**What changed.** Added `tools/library.py` — a searchable corpus of markdown entries, ranked by
semantic similarity using a local `all-minilm` embedding model — alongside the existing
`memory.md`. Also added `fetch_url`, so "research" can mean actually looking something up
rather than only reasoning over what's typed in.

**Why.** `memory.md` was doing two incompatible jobs. Conversational continuity wants to be
small and *always* in context. Accumulated knowledge wants to be unbounded and retrieved *only
when relevant*. One file cannot be both: as memory grows, every single turn pays for knowledge
it doesn't need, and the model's attention gets diluted by irrelevant notes.

So: memory stays small and is injected into the system prompt every turn. The library is never
injected wholesale — the model calls `search_library` when a query warrants it, and pays context
only for what comes back.

**Design decisions and their trade-offs:**

- **Semantic embeddings over keyword/TF-IDF search.** Keyword search is dependency-free and
  deterministic, but purely literal — a query for "car" never finds an entry about "vehicle".
  Since Ollama is already running, a 46MB embedding model is nearly free and needs no new pip
  dependency, just another HTTP call. *Known limitation:* each entry is embedded as one vector,
  and `all-minilm`'s effective context is a few hundred tokens, so a long write-up's tail barely
  influences its ranking. Chunked embeddings are the fix when this bites.

- **One markdown file per entry, not a database.** Keeps entries human-readable, hand-editable,
  and diffable — consistent with how `memory.md` already works. `library/index.json` holds the
  vectors, is gitignored (it churns on every save and would bloat diffs), and is fully
  regenerable via `rebuild_library_index` — which is exposed as a tool precisely so a fresh
  checkout can recover.

- **Proactive saves, but announced.** The model saves research on its own initiative rather than
  waiting to be asked, but must tell the user it did. Silent auto-save would mean a growing
  store nobody is tracking; manual-only would mean it rarely happens.

- **stdlib `html.parser` over `beautifulsoup4`.** Preserved the requests-only dependency budget
  at the cost of cruder extraction on messy HTML — no smart handling of nav/footer boilerplate.
  A deliberate application of principle 2. Revisit if fetches turn out to be consistently noisy.

**Not solved by this.** The library only helps if the agent can find information in the first
place. See the tide entry above.

---

## 2026-08-14 — First tests, and the bug they found

**What changed.** The project had no tests at all. Added a pytest suite covering every tool plus
`main.py`'s Ollama-connectivity logic, entirely mocked — no network, no subprocess, no live
Ollama needed. Also pinned `urllib3<2`.

**Why mocked throughout.** A test suite that needs an 18GB model resident to run is a test suite
nobody runs.

**The bug.** `list_directory` called `os.listdir` on each subdirectory to report an item count,
unguarded. A single permission-denied subfolder raised and discarded the **entire** listing.

The interesting part is why it survived review: `search_files` does conceptually the same walk
and never had this problem, because `os.walk` swallows the equivalent `OSError` internally. Two
functions that look equivalent, one silently protected by its stdlib call and one not. That
asymmetry is invisible unless you either read `os.walk`'s implementation or write the test.

**The urllib3 pin.** Apple's system Python links against LibreSSL, not OpenSSL, and urllib3 v2
warns loudly on *import* — so it appeared on every pytest run and every `main.py` startup, even
though no test opens a real connection. Pinning below v2 was cleaner than silencing the warning
in pytest config, which would have left it in the user's face during normal use.

---

## Before this log (reconstructed from the code and commit history)

*Written after the fact — this reasoning is inferred from the code and commits, not recorded at
the time.*

The architectural decision that shapes everything else: tools are exposed via **Ollama's native
function-calling**, with JSON schemas generated automatically from each function's signature and
Google-style docstring (`tools/__init__.py`). The model returns a structured `tool_calls` list.

The alternative — prompting the model to emit JSON and regex-scraping it out of the response —
is what the project moved *away* from. Native calling removes a whole class of parse failures
and, combined with auto-discovery, is what makes principle 3 real: adding a tool is genuinely
one file with no schema and no registration boilerplate.

Two supporting choices: streaming (`stream=True`) so a live indicator can show during the long
stretches qwen3 spends generating reasoning tokens, rather than dead air; and `think=True`, which
routes reasoning to a separate field so `content` arrives clean with no `<think>` tags to scrub.

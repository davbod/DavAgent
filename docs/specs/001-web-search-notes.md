# 001 — Web search: research notes (spec not yet written)

**Status:** superseded by `001-web-search.md`
**Date:** 2026-08-15 (research attempt), 2026-08-17 (salvaged and written up)

> **Update, same day:** the workflow completed after ~50 hours, shortly after this was written,
> and produced a spec — see `001-web-search.md`. This file is kept as the record of what was
> salvageable mid-run, and because its provenance table is what the synthesis agent read.
> **The Ollama lead below is now confirmed** (`POST https://ollama.com/api/web_search`, Bearer
> auth) and is the spec's preferred backend.

These are the findings that survived, kept because they cost real effort and are worth not
re-running.

## Provenance — read before trusting anything here

| Finding | How it was obtained | Confidence |
|---|---|---|
| Repo conformance checklist | Agent read the codebase directly; completed normally | High — verifiable against the repo |
| Search-engine reachability table | Agent made **real HTTP requests** and recorded status codes | Medium-high — measured, but on one residential IP on one day |
| Ollama native web search API | Surfaced in a web search; **since CONFIRMED live** — see update above | ~~Low~~ → High |
| Security judge notes | Judged proposals that had already died; scores meaningless | Low — reasoning may be reusable, scores are not |

Raw dumps are in `.workflow-research/001-web-search/` (gitignored).

## Measured: keyless search endpoint reachability

An agent probed candidate keyless endpoints directly. This is the most valuable salvaged
result, because it is measurement rather than recollection.

**DuckDuckGo HTML endpoint under sustained querying** — it rate-limits, then recovers:

```
after_1min   http=202  results=0   captcha=1
after_2min   http=202  results=0   captcha=1
after_3min   http=200  results=10  captcha=0
after_4min   http=200  results=10  captcha=0
after_6min   http=200  results=10  captcha=0
after_10min  http=200  results=10  captcha=0
```

Reading: DDG answers `HTTP 202` with a captcha page when it decides you're a bot, and clears
on its own after roughly **3 minutes**. It does not appear to hard-ban. So a keyless DDG
backend is viable *if* the tool detects the 202/captcha state explicitly and reports a
"rate-limited, retry shortly" string rather than handing the captcha HTML to the model — the
same class of mistake as the `text/HTML` bug on 2026-08-14.

**Other keyless engines, single probe each:**

| Engine | Result | Usable? |
|---|---|---|
| `wiby.me` | `200`, returned real results | Yes — but a small independent index, thin on current/local data |
| `startpage.com` | `200`, but body was "Verifying your request… Loading…" | No — JS gate, and `fetch_url` cannot run JS |
| `ecosia.org` | `403` — "Ecosia Firewall / confirm you're not a robot" | No |
| `yep.com` | `403` — Cloudflare block | No |
| `stract.com` | `404` | No |

The startpage result is worth noting: it fails the *same* way `weathersa.co.za` did in the tide
test — HTTP 200 with no server-rendered content. Any search backend must be checked for this,
not just for status codes.

## Unverified lead: Ollama's own web search API

An agent surfaced references to Ollama offering a web search / fetch API. **This was never
verified** and may not exist in the form implied. If real, it is strategically interesting for
DavAgent specifically: Ollama is already a hard dependency, so it would add no new vendor, and
key handling would follow whatever Ollama already uses.

**First task on resuming: confirm or kill this**, since it would materially change the backend
decision.

## Repo conformance

A complete conformance guide for a new `tools/search.py` was produced and is saved at
`.workflow-research/001-web-search/research-C-repo-conformance.md`. One noted sharp edge worth
repeating here: **every `.py` in `tools/` is imported at package-import time**, whether or not
it exports `TOOLS` — so import-time side effects in a new tool module affect every run,
including the test suite.

## Still open (the actual research gaps)

- Keyed backends (Brave, Tavily, Serper, SerpAPI, Google CSE) — free tiers never assessed.
- Result formatting for a 30B local model — how many results, what shape.
- Interaction with `fetch_url` when top results are JS-only or paywalled.
- Loop guardrails, which the tide test showed are missing.

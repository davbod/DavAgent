# Specs

One spec per segment of work, named `NNN-short-name.md`, numbered in the order they were
started. A spec is written and **approved by the project lead before implementation begins**.

Specs are not permanent documentation — they capture the intent and the agreed shape of a
change at the moment it was decided. They are not rewritten to match what shipped. If the
implementation ends up diverging, that divergence and its reason belong in `DEVLOG.md`.

## Process

1. **Research & design.** Explore the problem and competing approaches — for anything
   non-trivial, in parallel, so designs are genuinely independent rather than variations on
   the first idea that surfaced.
2. **Spec.** Draft the document below. Open questions must be real decisions for the lead,
   each with a recommended default — not questions answerable by reading the repo.
3. **Approve.** The lead signs off, or redirects. No implementation before this.
4. **Implement.** Build against the spec, with tests. Tests must pass with no network access
   and no running Ollama.
5. **Review.** Adversarial review of the result, then a `DEVLOG.md` entry recording what was
   learned — especially anything that contradicted the spec.

## Status values

`draft` → `awaiting approval` → `approved` → `implemented` (or `rejected` / `superseded by NNN`)

## Template

```markdown
# NNN — Title

**Status:** draft
**Date:** YYYY-MM-DD

## Problem
What is broken or missing, and the concrete evidence for it. Reference real
observed behaviour wherever possible rather than a hypothetical.

## Goals
What this change must achieve.

## Non-goals
What this deliberately does not do. Being explicit here prevents scope creep
and pre-empts "why didn't you also..." later.

## Design
The approach, concretely: tool signatures, data shapes, control flow. Enough
that someone else could implement it.

## Test plan
One line per test. All must run without network or a live Ollama.

## Security notes
Key handling, untrusted input, anything that touches the user's filesystem or
sends data off the machine.

## Open questions
Decisions for the lead, each with a recommended default.

## Rejected alternatives
What was considered and why it lost. This is the section future-you will
actually want.
```

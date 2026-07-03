# Milestone 4 Progress

## Goal
Vision — Jarvis can see. Give Jarvis the ability to take in an image (screenshot, camera, or
file) and reason about it in conversation, on top of the existing voice loop and memory.

Mental model still holds: "only the ends change, the brain stays the same" —
`get_jarvis_response()` keeps taking messages and returning text; vision means the input side
can now carry an image block alongside text, not just transcribed speech.

## Carried over from Milestone 3 (deferred, see teacher/MILESTONE3_PROGRESS.md)
- Memory classification (topic sorting — the "Obsidian clerk" idea, as a plain function first,
  agent later only if lag demands it).
- Index-based smart lookup to replace full-file replay (memory file currently grows unbounded
  and is fully loaded into context every run — will degrade as it grows).
- Bassam wants to revisit these after the remaining milestones, before/around the PC-control
  API work (M5).

## Open questions (work through with Bassam before building)
- What's the image source for v1 — a screenshot of the PC, a webcam frame, or a file path
  Bassam names out loud? (Pick ONE for the first version.)
- How does an image get attached to a turn in `history`? (Anthropic messages support content
  blocks: a list of `{"type": "image", ...}` and `{"type": "text", ...}` instead of a plain
  string — Bassam should read the docs and propose the shape.)
- What triggers vision — a voice command like "look at my screen," or every turn? (Cost and
  latency say: on command.)
- Does anything about the saved memory format need to change when a turn included an image?

## Not started
Everything — this doc created 2026-07-03 at M3 close. First step: decide the v1 image source
and have Bassam sketch the flow of one vision turn before any code.

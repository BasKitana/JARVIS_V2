# Milestone 5 Progress

## Goal
Vision + PC control — Jarvis can see the screen and act on it (click, type) via Anthropic's
official `computer` tool type. Originally this was Milestone 4; renumbered to M5 on 2026-07-06
when Bassam decided filesystem/shell control (now M4) should be built first, since it exercises
the same tool-use loop mechanic without the added risk of real, unsupervised mouse/keyboard
control on the actual desktop.

Mental model still holds: "only the ends change, the brain stays the same" —
`get_jarvis_response()` keeps taking messages and returning text; this milestone adds tool use so
Claude can decide mid-conversation that it needs to see/act, rather than the code deciding for it.

## Decisions made 2026-07-05, revised 2026-07-06
- **No local LLM.** Considered and explicitly dropped — the only motivation was cost, and for a
  personal single-user assistant that's not a real problem worth the reliability hit. Jarvis
  stays on Claude's API for everything, indefinitely.
- **REVISED 2026-07-06 — Anthropic's official `computer` tool, not custom schemas.** Originally
  planned as custom tools (`take_screenshot`, `click`, `type_text`) for portability and full
  understanding of the mechanic. Reversed after weighing it: Claude has been specifically trained
  on the `computer` tool's exact action shapes (screenshot/click/drag/scroll/key), so click/type
  accuracy should be meaningfully better than an untrained custom schema. Trade-off accepted:
  beta API surface, larger action set to wire up, less portability if a local model is ever
  reconsidered.
- **Model: Sonnet 5** for this milestone (consistent with M4's Sonnet-for-tasks split).
- **Trigger mechanism: tool use, not keyword matching.** Bassam correctly identified that
  if/else or keyword detection ("screen", "look") is brittle and produces false positives
  (e.g. "screen quality is bad" should NOT trigger a screenshot). Claude decides whether to call
  the tool based on understanding the request, same as any tool-use flow.
- **No separate silent-description step.** Earlier idea was: screenshot -> silent description ->
  save to memory -> speak the actual answer separately. Dropped — with tool use, Claude gets the
  image as a tool result and produces one final answer that already reflects the screen. That
  final answer is the only thing that goes to `voice.Speak()` and the only thing that goes to
  `write_to_memory` — no new memory-writing logic needed beyond whatever M4 already introduces.
- **Safety flag (Bassam's explicit call, one warning given and respected):** giving Jarvis real
  mouse/keyboard control on the actual desktop has real blast radius (misclick/mistype doing
  something unintended). Bassam wants full click+type capability anyway. This is exactly why the
  kill switch below is a hard requirement before this milestone runs against the real desktop,
  not an optional nice-to-have like the M4 shell tool's "trust the model" stance.

## Carried over from Milestone 3 (deferred, see teacher/MILESTONE3_PROGRESS.md)
- Memory classification (topic sorting — the "Obsidian clerk" idea, as a plain function first,
  agent later only if lag demands it).
- Index-based smart lookup to replace full-file replay (memory file currently grows unbounded
  and is fully loaded into context every run — will degrade as it grows).

## Tool-use loop design (locked 2026-07-05)
Claude's `content` list per response can hold multiple blocks at once (text + tool_use together)
— the model can narrate a filler line ("let me check your screen") in the same response as the
tool_use block, no extra API call needed for the filler. Same trick M4 uses for the
Haiku-to-Sonnet handoff.

Loop, per user turn:
1. Call the model with the running `history` + the tool definition(s).
2. If the response has a `tool_use` block: speak/collect any text block in the same response as
   the filler line, execute the real action (screenshot/click/type via the `computer` tool),
   send the result back as a `tool_result`, and go back to step 1.
3. If the response is plain text with no `tool_use`: that's the final answer — speak it, and it's
   the only thing that goes to `write_to_memory`.
4. Cap at **20 tool calls in one turn** (raised from 16 on 2026-07-06 to match M4's cap). If the
   cap is hit without reaching a plain-text response, stop and tell Bassam it got stuck rather
   than looping forever.

This is a while-loop, not a fixed sequence — a given request might take 1 tool call or 8; the
code doesn't know or assume how many, it just keeps going until step 3 or the cap.

## Kill switch (locked 2026-07-05 — hard requirement before this milestone touches the real desktop)
A global hotkey (tentatively ctrl+shift+s, exact key TBD) that hard-kills the whole Jarvis
process — a panic button for "it's doing something wrong," not a graceful stop. Needs its own
background thread/OS-level key hook, since the main loop is synchronous and blocks on the mic,
the API call, and tool actions — a hotkey check inside the same loop wouldn't be watched while
those are blocking.

## Open questions (work through with Bassam before building)
- Confirm the exact `computer` tool version/beta header to use (`computer_20251124` or whatever
  is current when this milestone starts) and the action set it requires implementing.
- How screenshots move from disk/memory to the API in the `computer` tool's expected content
  block shape (Bassam to confirm from Anthropic's current computer-use docs).
- Which library/mechanism for the global hotkey listener on Windows (needs to work while the main
  thread is blocked on network/mic calls).
- Beyond the kill switch, no per-action guardrails (e.g. confirm-before-click) are designed yet —
  revisit before this actually runs against the real desktop.

## Not started
Everything — this doc renumbered from M4 to M5 on 2026-07-06 after Bassam decided to build
filesystem/shell control first. Next session (once M4 ships): confirm the current shape of
Anthropic's `computer` tool in their docs, then wire up the kill switch before any real
click/type execution.

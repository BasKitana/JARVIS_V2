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

## Tool-use loop design (locked 2026-07-05, cap dropped 2026-07-10)
Claude's `content` list per response can hold multiple blocks at once (text + tool_use together)
— the model can narrate a filler line ("let me check your screen") in the same response as the
tool_use block, no extra API call needed for the filler. Same trick M4 uses for the
Haiku-to-Sonnet handoff.

Loop, per user turn:
1. Call the model with the running `history` + the tool definition(s).
2. If the response has a `tool_use` block: execute the real action (screenshot/click/type via the
   `computer` tool), send the result back as a `tool_result`, and go back to step 1.
3. If the response is plain text with no `tool_use`: that's the final answer — speak it, and it's
   the only thing that goes to `write_to_memory`.

**No iteration cap** — matches the M4 call Bassam made ("let it run infinitely, I don't care"),
extended to M5 on 2026-07-10 ("forget about having a maxima of operations"). The original design
above called for a 20-call cap; explicitly dropped. `jarvis_EMK.py`'s loop is a plain `while True`
with no counter, and `jarvis_screen_personality.txt` has no operation-limit language.

This is a while-loop, not a fixed sequence — a given request might take 1 tool call or 8; the
code doesn't know or assume how many, it just keeps going until step 3.

## Kill switch (locked 2026-07-05 — hard requirement before this milestone touches the real desktop)
A global hotkey (tentatively ctrl+shift+s, exact key TBD) that hard-kills the whole Jarvis
process — a panic button for "it's doing something wrong," not a graceful stop. Needs its own
background thread/OS-level key hook, since the main loop is synchronous and blocks on the mic,
the API call, and tool actions — a hotkey check inside the same loop wouldn't be watched while
those are blocking.

## Resolved questions (confirmed 2026-07-10 against Anthropic's current docs)
- **Tool version/beta header:** `computer_20251124`, requires `betas=["computer-use-2025-11-24"]`
  on a `client.beta.messages.create(...)` call (not the plain `client.messages.create`). Schema-less
  — no `input_schema` to write, the action set is built into the model.
- **Screenshot content block shape:** a `tool_result` for a `screenshot` action returns
  `content: [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": <b64>}}]`
  — confirmed against the official docs, not guessed.
- **Resolution limit:** Sonnet 5 (and Opus 4.7/4.8) accept up to 2576px on the long edge. Bassam's
  real screen layout, queried via `System.Windows.Forms.Screen.AllScreens` (not just taken on his
  word): primary monitor at (0,0) 2560x1080, secondary (portrait) at (2560,-534) 1080x1920 —
  combined virtual desktop is 3640x1920, over the cap, so the screenshot sent to the API is
  downscaled by `2576/3640 ≈ 0.708` to 2576x1359. Coordinates Claude returns need to be divided by
  that same scale factor and have the virtual-screen origin `(0, -534)` added back in to map to
  real screen pixels — this conversion is not implemented yet, only the constants are in place.

## Open questions (still unresolved)
- Which screenshot/automation library — `mss` was proposed (grabs an arbitrary bounding box,
  needed for the two-monitor combined capture; `pyautogui.screenshot()` only grabs the primary
  monitor by default on Windows) but not yet chosen/installed.
- Global hotkey listener library for the kill switch — still open.
- Beyond the kill switch, no per-action guardrails (e.g. confirm-before-click) are designed yet —
  revisit before this actually runs against the real desktop.

## Session 2026-07-10 — where this actually stands, read before continuing
Two new files exist: `jarvis_EMK.py` (the loop + tool dispatch, Bassam renamed it from the
originally-suggested `jarvis_screen.py`) and `jarvis_screen_personality.txt` (Sonnet's system
prompt for this loop).

**`jarvis_EMK.py`:**
- `COMPUTER_TOOL` declared with the computed 2576x1359 dims and the virtual-screen constants
  above.
- `jarvis_screen_action(user_command)` — the while-loop, structurally mirrors `jarvis_cmd.py`'s
  `jarvis_command()`: call the model, append the assistant turn, detect a `tool_use` block, run
  it, append a `tool_result`, loop; return `{"role": "assistant", "content": text}` on plain text.
- `handle_computer_action(input)` dispatches on `input["action"]` for all 11 actions the tool can
  request (`screenshot`, `left_click`, `type`, `key`, `scroll`, `right_click`, `double_click`,
  `mouse_move`, `hold_key`, `wait`, `zoom`) to matching handler functions.
- **Every single handler function is still `raise NotImplementedError`** — `take_screenshot`,
  `click_at`, `type_text`, `press_key`, `scroll_at`, `right_click_at`, `double_click_at`,
  `move_mouse_to`, `hold_key`, `wait`, `zoom_region`. Nothing about this can actually see or touch
  the screen yet. Calling any of them crashes the loop (uncaught exception), which is an
  intentional stopgap for now (fail loud during development) but needs revisiting before this
  runs unattended.

**`jarvis_screen_personality.txt`:** identity/environment/workflow mirroring `Jarvis_Tasking.txt`'s
structure, plus two things specific to this milestone:
- Tells Sonnet the combined-virtual-desktop layout (which side of the image is which monitor) so
  it can reason about screenshots correctly.
- The final-response rule is the *opposite* of M4's "keep it short" instruction, deliberately:
  since neither Haiku nor Bassam ever see the screenshots, Sonnet's final text is the only channel
  carrying what was actually seen. Framed as professional audio-description for a blind listener —
  maximally detailed and expressive, but still natural spoken prose, not a technical log.
- Explicitly tells Sonnet only 4 of the 11 actions have a real code path (vs. falling through to
  an "unhandled action" string) and to say so honestly rather than pretend an unavailable action
  worked — same lesson M4 learned the hard way, applied here before it could bite for real.

**Next session:** pick a screenshot/automation library (`mss` proposed, not chosen) and implement
`take_screenshot()` first — nothing else in the loop is testable until Jarvis can actually see the
screen. Kill switch still not built; still a hard requirement before any of this runs against the
real desktop per the locked decision above.

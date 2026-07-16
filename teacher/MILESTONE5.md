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
  something unintended). Bassam wants full click+type capability anyway. This originally made a
  kill switch (see below) a hard requirement before this milestone could run against the real
  desktop. **REVISED 2026-07-15 — kill switch dropped entirely, Bassam's call.** In its place:
  a "WHEN TO STOP AND ASK" rule in `jarvis_screen_personality.txt` (see below) — a judgment-call
  guardrail, not a hard-coded action list, that has Sonnet pause and ask before anything
  destructive/irreversible/private instead of a panic-button process kill.

## Carried over from Milestone 3 — both now CLOSED (2026-07-15), kept for history
- ~~Memory classification (topic sorting — the "Obsidian clerk" idea)~~ — effectively shipped:
  `memory_clerk()` is that clerk, built as a Haiku call rather than a plain function.
- ~~Index-based smart lookup to replace full-file replay~~ — closed by the scope cut below, and
  the underlying concern (memory file growing unbounded and fully replayed every run) no longer
  holds: the clerk distills to `Jarvis_Mind.md` and clears `Jarvis_Chat.md` each turn.

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

## Kill switch — DROPPED (2026-07-15, Bassam's call)
Originally locked 2026-07-05 as a hard requirement before this milestone touches the real desktop:
a global hotkey that hard-kills the whole Jarvis process, a panic button for "it's doing something
wrong." Explicitly dropped instead of built. The per-action guardrail below (WHEN TO STOP AND ASK)
covers the actual risk this was meant to catch — Sonnet stopping itself before anything dangerous
rather than Bassam needing to kill the process after the fact.

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

## Resolved since 2026-07-10
- **Screenshot library: `mss`**, as proposed — grabs the arbitrary two-monitor bounding box,
  downscales with PIL to the exact dims declared in `COMPUTER_TOOL`. Combined with `pyautogui`
  for mouse/keyboard actions. Both installed and wired in `jarvis_EMK.py`.
- **All 11 action handlers are implemented** — `take_screenshot`, `click_at`, `type_text`,
  `press_key`, `scroll_at`, `right_click_at`, `double_click_at`, `move_mouse_to`, `hold_key`,
  `wait`, `zoom_region` all have real code paths now, not `NotImplementedError`. Coordinate
  conversion (`to_real_coords`) between the downscaled image Sonnet sees and real screen pixels
  is implemented and in use by every click/scroll/zoom handler.
- **Per-action guardrails, two of them, both prompt-level (no new code needed):**
  1. Shutdown/sleep/restart confirmation in `jarvis_personality.txt` (Haiku's layer) — these three
     actions require Jarvis to ask and wait for an explicit yes on the next turn before delegating,
     since Haiku's conversation history persists across turns and can track that confirmation.
  2. "WHEN TO STOP AND ASK" in `jarvis_screen_personality.txt` (Sonnet's screen-loop layer) — a
     judgment call, not a fixed list: before anything destructive/irreversible/private, Sonnet
     stops, doesn't act, and makes its final response a question instead of a click. That question
     flows back through Haiku same as any other report, and Bassam's next reply re-delegates with
     the answer folded in. No pause/resume mechanism needed in the loop itself — it already returns
     final text the moment Sonnet stops calling tools, which is exactly what this repurposes.

## Open questions (still unresolved)
- None specific to the screen-control mechanic itself — that half of M5 is done. Everything still
  open is in "The four remaining tasks" section at the bottom of this file.

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
- **Update 2026-07-15: all handlers are implemented now** (see "Resolved since 2026-07-10" above) —
  this session's note about `NotImplementedError` everywhere is history, not current state.

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

**(Historical note — superseded):** this session's "next session" pointer said to pick a
screenshot library and implement `take_screenshot()` first, with the kill switch still required
before running against the real desktop. Both are resolved now — see "Resolved since 2026-07-10"
above and the kill-switch section (dropped, not built).

## Interim detour: Spotify control (started 2026-07-15, working end-to-end same day)
Bassam pulled this forward from the post-milestone backlog in the root `CLAUDE.md` — was originally
slotted for after the coding-ability milestone, built immediately instead, in parallel with M5's
screen control. M5's own work above (kill switch, `take_screenshot()`) was unblocked and
independent of this the whole time — still the next thing to pick up.

**Goal:** Jarvis can control Spotify playback by voice — play/pause, skip, search-and-play a
track/artist/playlist, liked songs, report what playlists exist. Also handles YouTube
search/play/open, no auth needed for that half. **Done, tested working.**

**Design decision — no LLM inside the media arm, unlike `jarvis_cmd`/`jarvis_EMK`.** Originally
planned as a `jarvis_cmd.py`-style sub-loop (its own Sonnet call, its own tool schema for
play/pause/search). Reversed once Bassam pointed out Spotify/YouTube actions are a small,
deterministic action set — not open-ended like a shell command or screen interaction — so a second
model call would just be unnecessary cost/latency. `Jarvis_media.py` is plain Python: Haiku
recognizes "this is a media request" and forwards the raw task text via the `media_control` tool;
`jarvis_media()` decides Spotify vs YouTube and calls a regex/keyword dispatcher directly, no
reasoning step in between.

**What got reused vs. rebuilt:** the older `jarvis` repo (`BasKitana/jarvis`, GitHub) already had
working Spotify + YouTube control — found via `gh api`/`gh` code search once Bassam confirmed he
was pointing at that repo, not `command_tool`. The `_spotify_*` httpx helper functions (token
refresh, device discovery/wake, retry-on-404/5xx) and the `handle_spotify`/`youtube_action`
regex dispatch logic were ported close to verbatim — proven code, not worth rewriting. What's new is
only the `jarvis_media()` entry point that ties that old logic into the tool-use architecture.

**Credentials:** old repo's `SPOTIFY_CLIENT_ID`/`SECRET`/`REFRESH_TOKEN` weren't available anymore
(different machine/project), so these were regenerated from scratch — registered a fresh app at
developer.spotify.com/dashboard, then a one-time `spotify_authorize_once.py` script (written,
run once to mint the refresh token, then deleted per its own instructions) drove the OAuth
Authorization Code flow: open the approval URL, paste back the `127.0.0.1:8888/callback?code=...`
redirect URL, exchange for a refresh token via `accounts.spotify.com/api/token`. All four values
(`SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `SPOTIFY_REDIRECT_URI`, `SPOTIFY_REFRESH_TOKEN`)
are now in `.env`, verified present via a throwaway presence-check script (values never echoed).
Scopes used: `user-modify-playback-state`, `user-read-playback-state`,
`user-read-currently-playing`, `user-library-read`, `playlist-read-private`.

**Wired into `Jarvis.py`:** `MEDIA_CONTROL_TOOL` added alongside `DELEGATE_TASK_TOOL`/
`DELEGATE_SCREEN_TOOL`; dispatch branch calls `jarvis_media()` (imported via
`from Jarvis_media import jarvis_media`). `system_prompts/jarvis_personality.txt` updated to
describe all three tools, including the "Spotify/YouTube always goes to `media_control`, even a
bare 'open Spotify'" carve-out, since the media subsystem's `_spotify_ensure_device()` already
handles launching the app if nothing's active.

**Open questions still unresolved:** "control" is Spotify-Connect-device playback only (the Web
API can't touch an arbitrary local player state that isn't Spotify-Connect-visible); which device
gets targeted when multiple are active is whatever `_spotify_device()`'s heuristic picks (first
`is_active`, else the first device in the list) — untested with genuinely multiple simultaneous
devices.

## Voice: SAPI -> Chatterbox -> edge-tts (2026-07-15)
Original entry point was renamed `Jarvis_Talking.py` -> `Jarvis.py`; system prompts moved out of
the repo root into `system_prompts/`. Both reflected below and in the main `CLAUDE.md`.

**Tried Chatterbox Turbo (`ChatterboxTurboTTS`), zero-shot voice cloning off a reference clip
pulled from a YouTube short via `yt-dlp`+`ffmpeg`.** Real, non-hypothetical bugs hit and fixed
along the way, in case this model/library comes up again:
- `norm_loudness()` multiplies the float32 waveform by a numpy-float64 gain scalar under NumPy 2,
  upcasting the whole clip to float64 and crashing every float32 layer downstream. Fixed with a
  small monkeypatch casting the output back to float32.
- Installing the community `chatterbox-streaming` fork (for lower-latency streamed playback)
  turned out to hard-pin incompatible numpy/librosa/transformers versions against `chatterbox-tts`,
  and both packages ship a colliding top-level `chatterbox` module — installing one corrupts the
  other's files on disk in a shared global environment (no venv on this project). Full
  uninstall/purge/reinstall was needed to recover; **conclusion: `chatterbox-streaming` needs its
  own dedicated venv to use at all, it cannot coexist with the base package globally.**
- Real GPU-latency bug found and fixed separately: Chatterbox's per-token generation rate degraded
  progressively over a long-running session (54 -> 19 tokens/sec, mel inference collapsing from
  ~20 it/s to 4.77 *seconds* per item). Root cause was VRAM pressure, not the model — `nvidia-smi`
  showed 7654/8188 MiB used on the RTX 4060, with Wallpaper Engine's continuous background
  rendering as the main competing consumer. Closing it stabilized the rate for the rest of the
  session.
- Kokoro-82M was evaluated as a faster alternative (RTF ~0.03-0.5 depending on hardware) but its
  built-in preset voices were rejected on quality grounds (tried `am_michael`, `am_puck` — both
  rejected). Voice cloning for Kokoro exists only via a separate community wrapper (`KokoClone`),
  not evaluated further once `edge-tts` was found.

**Landed on `edge-tts`** — free, piggybacks on Microsoft Edge's own neural "Read Aloud" voices via
an undocumented-but-widely-used API, no key, no paid tier, no GPU/VRAM involvement at all. Voice:
`en-US-EricNeural`. This replaced Chatterbox entirely in `Jarvis.py` — the model loading, the
reference clip, the norm_loudness monkeypatch, `numpy`/`sounddevice` are all gone. `speak(text)`
is now: synthesize to a temp mp3 via `edge_tts.Communicate(...).save(...)` (async, wrapped in
`asyncio.run`), play it blocking via `playsound` (pinned to `1.2.2` — newer versions fail to build
on this setup), delete the temp file. Simpler than what it replaced, not just faster.

## SCOPE CLOSED — M5 is the final milestone (2026-07-15, Bassam's call)
There is no Milestone 6. Bassam cut the planned coding-ability milestone and the entire
post-milestone backlog (email integration, Claude Code hand-off, self-healing/watchdog, Obsidian
memory backend, graph-based memory, model routing) on 2026-07-15. The four tasks below are the
only remaining work on Jarvis. When they're done, the project is done — do not roll over into a
`MILESTONE6.md`, and do not re-propose anything from the cut list. Full record of what was cut and
why: the "Scope is closed" section in the root `CLAUDE.md`.

Two consequences worth noting explicitly:
- The **graph-memory** idea (Bassam's, 2026-07-10) is cut and also largely obsolete — it targeted
  unbounded flat-file replay growing context every run, which the `memory_clerk()`
  distill-to-`Jarvis_Mind.md`-and-clear architecture already solves from another angle. This also
  permanently closes M3's deferred "index-based smart lookup" item listed further up this file.
- The **self-healing/watchdog** backlog item is cut, but task 4 below (restart on voice command) is
  its near-cousin and stays in scope. Only the crash-triggered half is gone.

## The four remaining tasks (all that's left on Jarvis)
None of it is specific to vision/screen-control anymore.

**Tasks 1 and 2 are one subsystem, not two.** Both are gates on the same question — "should what
the mic hears right now count as input?" Barge-in gates on *Jarvis is currently speaking*; the
hotkeys gate on *Bassam said no*. They share state and both require the same `listener()` rework.
Design them together or the gate gets built twice.

1. **Interrupt/barge-in** — talk over Jarvis mid-response and have it stop. Real code change needed
   (not a prompt tweak) since `speak()` blocks the whole script on `playsound()` — no way to
   interrupt a single-threaded blocking call. The harder problem underneath is not threading: for
   barge-in to work the mic must be recording *while* audio is playing, which means Jarvis hears
   his own voice through the speakers. That's the actual design problem to solve. Not started.
2. **Mic-mute hotkeys** (added 2026-07-15) — hold `Ctrl+Win` to mute the mic for as long as it's
   held, so Jarvis doesn't pick up dictation while Bassam uses WhisperFlow; `Shift+M` to toggle
   mute on/off manually. Needs a global keyboard hook (works while Jarvis isn't focused) plus the
   shared mic-gate state from task 1. Not started.
3. **`memory_clerk()` backgrounding** — currently runs synchronously every turn in `Jarvis.py`,
   adding a full extra Haiku API round-trip before the loop goes back to listening. Needs a
   background thread, plus a real race condition needs solving first: `memory_clerk()` reads
   `Jarvis_Chat.md` then truncates it after a slow API call — if backgrounded, a new turn's
   `write_to_memory()` could append to the file mid-cleanup and get silently wiped when the clerk
   call finishes and clears the file. Not started.
4. **Reload/self-restart on voice command.** Not started.

Suggested order (proposed 2026-07-15, not yet locked): 3 first (smallest, contained, and the only
one with a live correctness bug), then 1+2 together as one mic-gating design, then 4.

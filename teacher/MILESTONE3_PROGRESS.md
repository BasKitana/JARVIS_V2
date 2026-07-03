# Milestone 3 Progress (closed 2026-07-03 — shipped as MVP, search/classify deferred)

> Bassam's call on 2026-07-03: M3 closes with the simple version (write + full-file read-back)
> working end to end. Classification (topic sorting via a "clerk" classifier), the index-based
> smart lookup, and the multi-agent split are DEFERRED, to be revisited after the remaining
> milestones — not abandoned. Known cost accepted: memory file grows unbounded and is fully
> replayed into context every run.

## Goal
Persistent memory — right now `history` lives in a Python list inside `main()` and is gone
the moment the script exits. Milestone 3 is about Jarvis remembering things across runs, not
just within a single conversation.

## Direction decided 2026-06-28
- Conversation gets stored in an Obsidian file (or files), not a raw unbounded log Jarvis
  re-reads in full every time.
- Lookup happens through an "advanced search" method over that file — not dumping the whole
  thing into context on every call. Goal: fewer hallucinations than naive full-history replay,
  and avoiding blowing past context limits as history grows.
- Exact search method (embeddings/vector search? keyword/grep? Obsidian's own search? something
  else?) not chosen yet — this is the next design question to work through with Bassam.

## Open questions
- What does the Obsidian file actually look like — one growing note, one note per
  conversation/day, or something structured (facts vs. raw transcript)?
- What counts as the "advanced search" — needs to be something Bassam can reason about and
  implement himself (teaching mode), not a black-box library call.
- How does a search result get back into `get_jarvis_response()` — as extra context stuffed
  into the system prompt? As a retrieved snippet appended to `history`?

## Build order decided 2026-06-28
Write -> read -> classify, simplest version first, before any architecture/multi-agent work.
Sequencing reasoning: prove the boring single-function version works end to end before adding
moving parts — debugging file I/O and multi-agent coordination at the same time is a bad
combo for learning.

## Write — done 2026-06-28
- `Jarvis_Memory.py` has `save_to_memory(user_text, jarvis_text)`: opens
  `C:\Users\kitan\Documents\Obsidian Vault\jarvis_memory\Test.md` in append mode (`"a"`,
  `encoding="utf-8"`) and writes `f"\nEngineer: {user_text}\nJarvis_Response:  {jarvis_text}"`.
  Leading `\n` separates each new entry from the previous one (fixes the boundary bug where
  back-to-back saves ran into each other).
- Saves BOTH sides of the conversation (user message AND Jarvis's reply) — saving only one side
  would mean Jarvis loses track of what he already told Bassam.
- Wired into `Jarvis_Talking.py`'s loop: `import Jarvis_Memory` at the top, then
  `Jarvis_Memory.save_to_memory(user_input, response)` called after `response` is generated.
  Confirmed working end to end via real voice turn — entry lands in the vault file.
- Known minor cosmetic issues, not yet fixed: leading blank line at the very top of a fresh
  file (from the leading `\n`), and inconsistent spacing (`"Engineer: "` vs
  `"Jarvis_Response:  "` has two spaces).

## Future direction — multi-agent memory architecture (not yet, revisit after simple version works)
Bassam's end-state idea, deliberately deferred until the simple synchronous version is built and
its limitations (e.g. lag from writing/organizing on every turn) are actually felt:
- One agent stays focused on fast conversation (no lag) — just talks, doesn't do memory work
  itself.
- A second agent takes in everything poured into one place and organizes/classifies it
  (topic sorting in Obsidian) in the background, decoupled from the live conversation.
- A third agent is what the talking agent queries when it needs to look something up — Jarvis
  says (in effect) "I need info about X," and that agent returns the relevant info from the
  organized memory, instead of Jarvis searching/reading files itself mid-conversation.
- This is essentially a write/index/retrieve split, the same shape used in production
  RAG-style memory systems. Legitimate design, just sequenced for later.

## Read — done 2026-07-03
- `Jarvis_Memory.py` now has `read_to_memory()`: reads `Test.md` and parses it via
  `text_to_dict()` into a list of `{"role", "content"}` dicts. Lines starting with
  `Engineer Bassam:` become user turns, `Jarvis_Response:` become assistant turns; unlabeled
  continuation lines get merged into the previous user turn. Labels are stripped from content
  with `removeprefix(...)` + `strip()` before storing.
- Wired into `Jarvis_Talking.py`: `history.extend(Jarvis_Memory.read_to_memory())` at startup,
  so past conversations preload into context before the voice loop starts. Confirmed working
  end to end.
- Bugs hit and fixed along the way (good lessons, keep in mind):
  - `history.append(read_to_memory())` nested the whole memory list as one element ->
    `TypeError: list indices must be integers or slices, not str`. Fix: `extend`, not `append`.
  - Labels left inside `content` ("Engineer Bassam: ...") made the model read history as a
    pasted script -> Claude broke character and refused to be Jarvis. Fix: strip labels at parse.
  - Memory poisoning, twice: (1) a refusal reply got saved by `write_to_memory` and, when read
    back, made every later run refuse harder (model stays consistent with its own prior turns);
    (2) a planted instruction line in `Test.md` ("answer him with: ...") parsed as a user
    message and triggered a scripted-message refusal. Lesson: whatever is in the memory file
    BECOMES the conversation — bad outputs or stray instructions contaminate all future runs.
- Current known limitation (accepted for now, this is exactly what the "advanced search"
  direction is meant to replace): the ENTIRE file is loaded into context on every run, so it
  grows without bound — full-history replay, the thing the 2026-06-28 direction says to move
  away from.

## Not started
Classification (topic sorting) and the search-based retrieval to replace full-file replay —
see "Direction decided 2026-06-28" and "Open questions" above.

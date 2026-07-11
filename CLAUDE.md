# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Jarvis is Bassam's personal learning project: a personal AI assistant built incrementally across milestones (text chat -> voice -> persistent memory -> vision + PC control -> coding ability). The point of the project is for Bassam to grow as a Python developer, not to ship Jarvis quickly. Stays on Claude's API throughout — a local-LLM milestone was considered and explicitly dropped (2026-07-05): the only motivation was cost savings, and for a personal single-user assistant the API cost isn't a real problem worth the reliability hit and infra work of self-hosting.

Milestones 1 (terminal text chat), 2 (voice, in/out both working), and 3 (persistent memory — closed as MVP: write + full-file read-back work; topic classification and index-based lookup deferred, see `teacher/MILESTONE3_PROGRESS.md`) are complete. Currently on Milestone 4 (vision + PC control, merged — see below). Coding ability is the planned milestone after that; whether Jarvis gets a frontend or stays background-only is an open decision to make once M4 is built.

### Current milestone progress doc — read this, not an old one

The live status doc is always `teacher/MILESTONE<N>.md` where N is the milestone in progress — right now that's [teacher/MILESTONE4.md](teacher/MILESTONE4.md). Read that file for the real state; treat it as the source of truth over any milestone narrative elsewhere (including this file). Completed milestones' progress docs (e.g. `teacher/MILESTONE2_PROGRESS.md`) are kept as history — don't open them for current status.

Rollover convention: write progress into the current `MILESTONE<N>.md` as work happens. When milestone N is actually done, delete `teacher/MILESTONE<N>.md`, create `teacher/MILESTONE<N+1>.md` with a fresh Goal/Not-started writeup, and update the link and milestone number in this section so future sessions point at the new file.

Mental model used throughout: "only the ends change, the brain stays the same" — `get_jarvis_response()` always just takes text and returns text; voice work only swaps how text gets in (input) and how it goes out (output).

### Post-milestone backlog (do not start until the coding-ability milestone is done)

Carried over from the older `jarvis` repo (BasKitana/jarvis), which had these working already. Not part of the current milestone plan — revisit only after coding ability ships:

- ~~Model routing (Haiku/Opus/Sonnet split)~~ — moot now that local LLM is dropped; everything stays on the API model chosen per task
- **Email integration** — read inbox, draft/send with confirmation, open links from mail (Gmail IMAP/SMTP)
- **Music/media control** — Spotify playback, YouTube search/play, liked songs, next/pause
- **Hand-off to Claude Code** — detect "engineer this" requests, sharpen into a prompt, launch Claude Code autonomously in a coding folder
- **Self-healing / watchdog** — auto-restart on crash, boot auto-start, crash logging
- **"Reload/restart yourself"** — hot-reload own code from a voice command
- **Obsidian as the memory backend** — structured facts file + idea capture + generated plans, not just a flat chat log

## Operating mode for this repo: teach, don't build

Bassam is an intermediate Python developer and wants a mentor, not a developer who writes code for him. This overrides default "just implement it" behavior:

- Never paste complete, ready-to-run solutions. Give skeletons, hints, or isolated single-concept examples, and have him write/adapt the rest.
- Ask what he thinks should happen before explaining or fixing.
- If his code has a bug, ask him to spot it before revealing it.
- Never agree just to be agreeable. If an approach will cause problems, say so plainly and explain why — even if he says to just do it his way (give one honest warning, then respect the choice).
- Bassam explicitly wants to be evaluated against senior-SWE judgment, not just told he's right. When he proposes a design or names a mindset/principle, actively check whether it actually holds up (right tool for the job size, sequencing, common pitfalls) and correct him plainly when it doesn't — even on small choices like "is this the right mindset."
- Walk through milestones one at a time; check his plan/reasoning before jumping into implementation for the next step.

## Environment / running code

- Python 3.13, installed at `C:\Users\kitan\AppData\Local\Programs\Python\Python313\python.exe`.
- No virtual environment yet — `anthropic` and `python-dotenv` are installed globally. This is a known, accepted tradeoff for now (single solo learning project), not an oversight.
- Secrets live in `.env` (currently holds `ANTHROPIC_API_KEY`). `.gitignore` covers `.env`, `__pycache__/`, `*.pyc`, and `.vscode/`.
- Run any script directly, e.g.:
  ```
  python Jarvis_Talking.py
  ```

## Code in this repo

- `Memory_Test.py` — isolated scratch exercise (not part of the final app) proving out the core "memory" concept: a list of `{"role": ..., "content": ...}` dicts that grows each loop iteration. Keep this concept in mind when reading or extending the real chat loop, since Claude's API is stateless and relies entirely on resending this list each call.
- `Jarvis_Talking.py` — the real entry point. `main()` builds a SAPI speaker (`win32com.client.Dispatch("SAPI.SpVoice")`) and a `speech_recognition` recognizer/mic, calibrates ambient noise once before the loop, then runs a `while True` chat loop: `listener(recognizer, mic)` records from the mic and transcribes with local Whisper, an empty-transcription guard skips to the next loop iteration if Whisper returns `''`, then it appends a user dict to `history`, calls `get_jarvis_response(history)`, appends the returned reply as an assistant dict, prints it, and speaks it via `voice.Speak(response)`. `get_jarvis_response` loads `.env`, builds the `anthropic.Anthropic` client, reads `jarvis_personality.txt` into a `system` prompt, and calls `client.messages.create(...)` with `messages=history`, returning just the reply text (`response.content[0].text`). See [teacher/MILESTONE2_PROGRESS.md](teacher/MILESTONE2_PROGRESS.md) for known issues (Whisper model reloads every call) and what's left.
- `Jarvis_Memory.py` — persistent memory (Milestone 3). `write_to_memory(user_text, jarvis_text)` appends both sides of each turn as labeled lines (`Engineer Bassam:` / `Jarvis_Response:`) to `C:\Users\kitan\Documents\Obsidian Vault\jarvis_memory\Test.md`. `read_to_memory()` reads that file and `text_to_dict()` parses it back into `{"role", "content"}` dicts, stripping the labels from content (labels left in trigger character-break refusals — learned the hard way). `Jarvis_Talking.py` calls `history.extend(read_to_memory())` at startup and `write_to_memory(...)` after each turn. Whole file is replayed into context every run — accepted MVP limitation, smart lookup deferred.
- `jarvis_personality.txt` — plain-text system prompt defining Jarvis's identity, tone, and hard constraints (no emojis, respect the hierarchy with Bassam, etc.). Now also tells Jarvis he has a voice (his replies are spoken aloud) and to avoid bullets/symbols that sound bad read aloud. Read fresh on every call inside `get_jarvis_response` — known minor inefficiency, not yet worth fixing.

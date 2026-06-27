# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Jarvis is Bassam's personal learning project: a personal AI assistant built incrementally across 6 milestones (text chat -> voice -> persistent memory -> vision -> PC control -> local LLM). The point of the project is for Bassam to grow as a Python developer, not to ship Jarvis quickly.

Milestone 1 (terminal text chat with Claude, same-session conversation memory, personality, key stored in `.env`) is functionally complete. Currently on Milestone 2 (voice), roughly half done.

### Milestone 2 progress and decisions

Detailed, current Milestone 2 status (output done, input working via local Whisper, known RAM issue, interrupt logic not started, next steps) lives in [teacher/MILESTONE2_PROGRESS.md](teacher/MILESTONE2_PROGRESS.md). Read that file for the real state — treat it as the source of truth over any milestone narrative elsewhere.

Mental model used throughout: "only the ends change, the brain stays the same" — `get_jarvis_response()` always just takes text and returns text; voice work only swaps how text gets in (input) and how it goes out (output).

## Operating mode for this repo: teach, don't build

Bassam is an intermediate Python developer and wants a mentor, not a developer who writes code for him. This overrides default "just implement it" behavior:

- Never paste complete, ready-to-run solutions. Give skeletons, hints, or isolated single-concept examples, and have him write/adapt the rest.
- Ask what he thinks should happen before explaining or fixing.
- If his code has a bug, ask him to spot it before revealing it.
- Never agree just to be agreeable. If an approach will cause problems, say so plainly and explain why — even if he says to just do it his way (give one honest warning, then respect the choice).
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
- `jarvis_personality.txt` — plain-text system prompt defining Jarvis's identity, tone, and hard constraints (no emojis, respect the hierarchy with Bassam, etc.). Now also tells Jarvis he has a voice (his replies are spoken aloud) and to avoid bullets/symbols that sound bad read aloud. Read fresh on every call inside `get_jarvis_response` — known minor inefficiency, not yet worth fixing.

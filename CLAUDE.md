# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Jarvis is Bassam's personal learning project: a personal AI assistant built incrementally across 6 milestones (text chat -> voice -> persistent memory -> vision -> PC control -> local LLM). The point of the project is for Bassam to grow as a Python developer, not to ship Jarvis quickly.

Milestone 1 (terminal text chat with Claude, same-session conversation memory, personality, key stored in `.env`) is functionally complete. Currently on Milestone 2 (voice), roughly half done.

### Milestone 2 progress and decisions

Milestone 2 (voice) is two halves: **output** (Jarvis speaks) and **input** (Bassam speaks to Jarvis). Mental model used throughout: "only the ends change, the brain stays the same" — `get_jarvis_response()` always just takes text and returns text; voice work only swaps how text gets in (`input()`) and how it goes out (`print()`).

**Done (output / text-to-speech):**
- Jarvis now speaks his replies aloud, working inside the chat loop. Implemented with direct Windows SAPI: `import win32com.client`, build `speaker = win32com.client.Dispatch("SAPI.SpVoice")` once at the top of `main()`, then `speaker.Speak(response)` in the loop after the `print`.
- `pyttsx3` was tried first and abandoned: confirmed bug on this machine where only the FIRST `runAndWait()` in a process produces audio; later calls report "spoke ok" with no error but stay silent. Re-initing the engine each loop made it worse (init caches the dead engine). Dropped to SAPI directly to skip the buggy wrapper layer. `win32com` is already installed (pyttsx3's sapi5 driver used it).
- Updated `jarvis_personality.txt` so Jarvis knows he has a voice (was previously told "all communication must be text-only", so he denied being able to speak). Also told him to avoid bullets/asterisks/symbols since they sound bad read aloud.
- Bumped `max_tokens` up from 100 (replies were getting cut off mid-sentence).

**Next time (input / speech-to-text) — NOT started:**
- Goal: replace `input("Chat:   ")` on line 9 with a `listen()` function that records the mic, converts speech to text, and RETURNS a string, so the rest of the loop is unchanged. Decision made: keep this as a function inside `Jarvis_Talking.py`, NOT a separate file/folder (avoid over-engineering), mirroring the existing `get_jarvis_response()` shape.
- `listen()` = two steps: (1) record audio from mic until Bassam stops talking, (2) hand audio to a speech-recognition engine that returns text.
- Two open decisions to make with Bassam before coding: (a) which STT engine — offline vs online, free vs accurate (not yet chosen); (b) interaction style — push-a-key-then-talk vs always-listening (not yet chosen).

**TODO before Milestone 3:** upgrade the voice from robotic SAPI to natural neural TTS using `edge-tts` (free, no API key, needs internet, already installed). It is async and outputs an mp3 file, so it needs a generate-file-then-play-it step rather than SAPI's single `Speak()` call. ElevenLabs was considered but rejected for now (paid, requires key). Do this before starting Milestone 3.

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
- `Jarvis_Talking.py` — the real entry point. `main()` builds a SAPI speaker once (`win32com.client.Dispatch("SAPI.SpVoice")`), then runs a `while True` chat loop: takes terminal input, appends a user dict to `history`, calls `get_jarvis_response(history)`, appends the returned reply as an assistant dict, prints it, and speaks it via `speaker.Speak(response)`. `get_jarvis_response` loads `.env`, builds the `anthropic.Anthropic` client, reads `jarvis_personality.txt` into a `system` prompt, and calls `client.messages.create(...)` with `messages=history`, returning just the reply text (`response.content[0].text`). Input is still typed (`input()`); turning that into voice (STT) is the remaining half of Milestone 2.
- `jarvis_personality.txt` — plain-text system prompt defining Jarvis's identity, tone, and hard constraints (no emojis, respect the hierarchy with Bassam, etc.). Now also tells Jarvis he has a voice (his replies are spoken aloud) and to avoid bullets/symbols that sound bad read aloud. Read fresh on every call inside `get_jarvis_response` — known minor inefficiency, not yet worth fixing.

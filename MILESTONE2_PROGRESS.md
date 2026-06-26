# Milestone 2 Progress

## Output (text-to-speech) — done
- Jarvis speaks replies aloud via SAPI (`win32com.client`, `voice.Speak(response)`).

## Input (speech-to-text) — working, started 2026-06-25
- `listener(recognizer, mic)` records from the mic (`sr.Recognizer` + `sr.Microphone`) and
  transcribes with local Whisper (`recognizer.recognize_whisper(audio, language="english")`).
- Ambient noise calibration (`adjust_for_ambient_noise`) moved to run ONCE in `main()` before
  the loop, not per-turn — per-turn calibration was eating ~1s at the start of every turn and
  caused clipped/missed speech ("doesn't hear me" symptom).
- `language="english"` forced on the Whisper call — without it, Whisper's auto language
  detection misfired on short/accented clips (e.g. heard "Hey" as Polish "który").
- Empty-transcription guard added in `main()`: `if user_input.strip() == "": continue` —
  Whisper occasionally returns `''` even on clear, well-recorded audio (model accuracy limit,
  not a bug); this prevents that from crashing the Claude API call (which rejects empty
  message content).
- Unrelated bug fixed along the way: `max_tokens` was `100000` in `get_jarvis_response`,
  which made the Anthropic SDK reject non-streaming calls. Lowered to a sane value.

## Known issue, not yet fixed — start here tomorrow
- `recognizer.recognize_whisper()` reloads the entire Whisper model from disk on every call
  (confirmed by reading `speech_recognition/recognizers/whisper_local/whisper.py` — no
  caching, `whisper.load_model(model)` runs every time). This is the RAM/slowness culprit.
  - Fix: stop using `recognize_whisper()`. Load the model once in `main()` with
    `whisper.load_model("base")`, pass it into `listener()`, and call
    `whisper_model.transcribe(...)` directly instead.
  - Open sub-problem: `model.transcribe()` wants raw audio (file path or numpy array), not
    the `AudioData` object `recognizer.listen()` returns — need to figure out that
    conversion (likely via `audio_data.get_wav_data()`).

## Not started
- Interrupt/barge-in logic: stop `voice.Speak()` mid-sentence when the user starts talking
  while Jarvis is speaking, and start listening again immediately. Needs `Speak()` called
  with the async flag (`SVSFlagsAsync`) instead of blocking, so the mic can be checked while
  he's talking.
- TTS upgrade: swap SAPI for `edge-tts` (free, natural voice, no API key, already installed)
  — decided before Milestone 3, not done yet.
- Text cleanup: strip residual markdown/symbols from Claude's replies before they're spoken,
  on top of the personality-prompt instruction already in place.

## Goal for next session
Finish Milestone 2: fix the Whisper RAM issue (load model once), then build interrupt logic.

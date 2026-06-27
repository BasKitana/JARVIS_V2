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

## RAM issue — fixed 2026-06-26
- Root cause confirmed: `recognizer.recognize_whisper()` reloaded the entire Whisper model
  from disk on every call (no caching in `speech_recognition`'s whisper recognizer).
- Fix applied: `whisper.load_model("base")` now runs once in `main()`, the model is passed
  into `listener(recognizer, mic, whisper_model)`, which calls `whisper_model.transcribe(...)`
  directly instead of `recognize_whisper()`.
- Conversion solved: `audio.get_wav_data()` -> write bytes to a `tempfile.NamedTemporaryFile`
  -> `transcribe(f.name)` (a file path), since `transcribe()` doesn't accept `AudioData`
  objects directly.
- Windows-specific gotcha hit and fixed: `NamedTemporaryFile(delete=True)` keeps the file
  handle open for the life of the `with` block, and Windows (unlike Linux/Mac) won't let a
  second process (ffmpeg, which Whisper shells out to) open a file that's still locked by
  another open handle — caused `PermissionError` / ffmpeg "Permission denied". Fix: use
  `delete=False`, write + flush + let the `with` block close the file (releasing the lock),
  *then* call `transcribe(f.name)` outside the `with` block, then `os.remove(f.name)`
  afterward to clean up manually.

## TTS upgrade — explored 2026-06-26, deferred
- Tried `edge-tts` (free neural TTS, no API key) as a SAPI replacement. CLI-tested several
  voices (`en-US-GuyNeural`, British/Australian options) via
  `edge-tts --voice <name> --text "..." --write-media test.mp3` — none landed on a voice
  Bassam actually liked (wanted something deeper, closer to Iron Man's Jarvis).
  Also considered ElevenLabs; rejected — free tier is too small (~10k chars/month) to use in
  an ongoing conversation, and Bassam doesn't want to pay yet.
- Decision: **keep SAPI for now.** Revisit TTS (try more `edge-tts` voices, or pay for
  ElevenLabs if it's worth it by then) after Milestone 6, once the full system is running
  end to end and it's clearer whether voice quality is actually worth the cost/effort.
- Code is back to SAPI-only; the `edge_tts`/`asyncio`/`playsound` imports tried during
  exploration were removed from `Jarvis_Talking.py`.

## GPU acceleration — added 2026-06-26
- Bassam has an RTX 4060, but `torch` was installed as the CPU-only build
  (`torch 2.12.0+cpu`), so Whisper was running on CPU the whole time despite a GPU being
  available — `torch.cuda.is_available()` returned `False`.
- Fixed by uninstalling `torch` and reinstalling the CUDA 12.4 build
  (`pip install torch --index-url https://download.pytorch.org/whl/cu124`), now
  `torch 2.6.0+cu124`. `whisper.load_model(...)` auto-detects and uses CUDA when available,
  no code change needed beyond the reinstall.
- Effect: Whisper transcribe time dropped from ~0.6-2.4s (CPU) to ~0.1-1.0s (GPU), which made
  upgrading to the `medium` model (better accuracy) affordable without the wait becoming
  painful — now running `whisper.load_model("medium")` instead of `"base"`.

## Whisper hallucination on noise — fixed 2026-06-26
- Background noise (keyboard clicks, mouse, fan) was getting picked up by
  `recognizer.listen()` as 2-4 second "speech" clips, and Whisper would hallucinate
  plausible-sounding text for them instead of returning empty — e.g. repeated "1.5% 1.5%..."
  loops, and "Thanks for watching!" (a known Whisper artifact from its YouTube-caption
  training data on silence/noise).
- Tried first: raising `energy_threshold` and disabling `dynamic_energy_threshold` (locks in
  the one-time calibrated threshold instead of letting it drift down over a session). Did not
  fully fix it — noise was still long/loud enough to pass the threshold.
- Real fix: `whisper_model.transcribe()` returns per-segment `no_speech_prob` (model's own
  confidence that a segment isn't speech) and `avg_logprob` (model's confidence in the actual
  words chosen). `listener()` now averages both across all segments and discards the
  transcription (returns `""`, caught by the existing empty-string guard) if
  `avg_no_speech_prob > 0.5` or `avg_logprob < -1.0`. The `avg_logprob` check was added second,
  after a separate hallucination (confident-sounding garbled Arabic) slipped through the
  `no_speech_prob` check alone. Both thresholds are starting guesses, not tuned values — loosen
  if real speech gets dropped, tighten if junk still gets through.

## Language auto-detect regression — fixed 2026-06-26
- When `listener()` was rewritten to call `whisper_model.transcribe()` directly (the RAM fix),
  the `language="english"` parameter that the original `recognize_whisper()` call had was
  dropped. Whisper's auto language detection then misfired on some English clips, transcribing
  them as Arabic. Fixed by passing `language="english"` to the new `transcribe()` call too.

## API key / billing dead end — resolved 2026-06-26
- Hit `anthropic.BadRequestError: credit balance too low` despite the Anthropic Console
  showing a real $5 balance. Root cause: a stale `ANTHROPIC_API_KEY` was set as a Windows
  **User-level environment variable** from some earlier session. `load_dotenv()` does not
  override existing environment variables by default, so every run kept silently using that
  old/wrong key from the OS environment instead of the current value in `.env`, no matter how
  many times the key was regenerated there.
- Fixed by clearing the stale variable (`[Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", $null, "User")`)
  and confirming in a genuinely fresh terminal (not just continued scrollback in an old one —
  that also caused false "still broken" reports) that `$env:ANTHROPIC_API_KEY` came back empty.
- Lesson: if an env var is set system-wide, `.env` changes are invisible until the stale
  var is removed — check `[Environment]::GetEnvironmentVariable(name, "User"/"Machine")`
  before assuming a `.env` edit didn't take effect.

## Not started
- Interrupt/barge-in logic: stop `voice.Speak()` mid-sentence when the user starts talking
  while Jarvis is speaking, and start listening again immediately. Needs `Speak()` called
  with the async flag (`SVSFlagsAsync`) instead of blocking, so the mic can be checked while
  he's talking.
- Text cleanup: strip residual markdown/symbols from Claude's replies before they're spoken,
  on top of the personality-prompt instruction already in place.
- `recognizer.pause_threshold` may be too short (default ~0.8s) — Bassam saw multi-word
  speech get cut off after the first word when pausing briefly mid-sentence. Worth bumping to
  1.2-1.5s if it keeps happening.
- TTS upgrade (deferred, see above) — revisit after Milestone 6.

## Milestone 2 status: done
Both halves (output via SAPI, input via local Whisper on GPU, loaded once) are working end to
end, with noise-hallucination filtering and correct language detection. Remaining items above
(interrupt logic, text cleanup, pause threshold, TTS upgrade) are nice-to-haves, not blockers —
fair to call Milestone 2 complete and move to Milestone 3.

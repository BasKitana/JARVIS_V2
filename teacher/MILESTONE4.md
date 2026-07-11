# Milestone 4 Progress

## Goal
Filesystem/shell control — Jarvis can create, read, modify, delete, or run anything on the
machine via one general-purpose `run_command` tool, dispatched through a two-model handoff so
the always-on conversational voice (Haiku) stays fast/cheap while actual task execution runs on
a stronger model (Sonnet 5). This was originally going to be paired with GUI/vision control as a
single milestone; split on 2026-07-06 so the tool-use loop mechanic gets proven out here first,
before adding real mouse/keyboard control's extra risk in M5 (see teacher/MILESTONE5.md).

Mental model still holds: "only the ends change, the brain stays the same" —
`get_jarvis_response()` still takes messages and returns text; this milestone adds a second model
call in the middle of that path, invisible to the memory/history layer (see below).

## Decisions made 2026-07-06 (before any code)
- **One general `run_command` tool, not a curated set of specific tools** (`list_directory`,
  `create_directory`, etc.). Bassam wants Jarvis to have full, unrestricted control — "if I tell
  him to do something, that's what I want," including destructive actions (delete, overwrite).
  Trade-off flagged and accepted: no undo, no confirmation step, a bad instruction or ambiguous
  request can cause real, permanent damage.
- **No safety gate on `run_command`.** Considered: a second "is this risky?" classifier call
  before executing, or a confirm-before-destructive-ops step. Rejected — Bassam wants full
  autonomy. The only "safety" is that Sonnet 5 (a strong model) is the one deciding what command
  to run, same trust already placed in Claude's judgment for whether to call any tool at all.
- **Two-model split: Haiku for conversation, Sonnet 5 for tasks.** Jarvis currently runs entirely
  on `claude-haiku-4-5` (see `Jarvis_Talking.py:51`) despite the old M4 doc saying Sonnet 5 — that
  decision was never implemented. This milestone actually introduces the split:
  - Haiku handles the normal back-and-forth conversation loop, fast and cheap.
  - Haiku has a `delegate_task` tool bound to it. When Haiku judges a request needs real system
    access, it calls `delegate_task` instead of answering directly.
  - Any text Haiku produces in that same response (e.g. "On it, Engineer") is spoken immediately —
    the same "text + tool_use in one response" trick M5's tool-use loop design uses, applied here
    to the handoff itself instead of a screenshot.
  - The `delegate_task` call kicks off a **separate Sonnet 5 tool-use loop**: its own system
    prompt (a task-executor persona, distinct from `jarvis_personality.txt`), bound to
    `run_command`, looping call -> tool_use -> execute -> tool_result -> repeat until it reaches a
    final plain-text answer or hits a cap of **20 tool calls** (same cap pattern as M5's GUI loop;
    both raised from an earlier 16-call draft to 20 on 2026-07-06).
  - Sonnet's final plain-text answer is spoken directly via `voice.Speak()` — it is NOT handed
    back to Haiku to rephrase.
- **Sonnet's system prompt must produce simple, spoken-friendly summaries.** Sonnet's task is to
  explain what it did and the result in plain language — not overly verbose, not technical
  command-by-command narration. This text is both spoken aloud and written to memory, so it needs
  to read naturally in both places.
- **Memory/history stays "one Jarvis."** Even though two models are involved, the shared
  `history` list and `write_to_memory` must not "see" the handoff. Haiku's filler text and
  Sonnet's final result get combined into a single assistant-turn string (e.g. "On it, Engineer...
  Done — created the folder at X.") and stored as one `Jarvis_Response` entry, same shape as any
  normal turn. This way, when Haiku reads memory back on a later turn (or later session), it sees
  a single coherent record of what "it" did, not a trace of an internal model handoff. This is the
  simple, spoken-friendly record — not a technical log (see below).
- **`run_command` schema: `command` + `working_directory`, not command-only.** A command-only
  string was considered (simpler schema, Claude folds `cd`/`Set-Location` into the string itself)
  but rejected: each `subprocess.run()` call is a fresh process, so directory context does not
  persist between tool calls. An explicit `working_directory` param (`subprocess.run(command,
  cwd=working_directory, ...)`) avoids Sonnet having to re-prepend a path prefix on every chained
  step of a multi-step task, and gives clean per-call logging of where each action ran. Default
  value for `working_directory` if Sonnet omits it: Jarvis's own process working directory.
- **Sonnet gets its own technical action-log memory, separate from the M3 spoken-memory file.**
  The merged `history`/`write_to_memory` record above only stores the simple spoken summary
  ("Done — created the folder at X"), not the exact commands run. Sonnet writes a detailed entry
  per delegated task (task description, exact commands run in order, their raw output, timestamp)
  to its own file, e.g. `C:\Users\kitan\Documents\Obsidian Vault\jarvis_memory\Sonnet_Actions.md`.
  Sonnet reads this file back at the start of every new delegated task (same full-file-replay
  pattern M3 uses for the main memory — accepted MVP limitation, same caveat about unbounded
  growth applies here too) so it has continuity with what it's actually done before, independent
  of whatever Haiku passes down in the `delegate_task` call.

## Carried over from Milestone 3 (deferred, see teacher/MILESTONE3_PROGRESS.md)
- Memory classification (topic sorting — the "Obsidian clerk" idea, as a plain function first,
  agent later only if lag demands it).
- Index-based smart lookup to replace full-file replay (memory file currently grows unbounded
  and is fully loaded into context every run — will degrade as it grows). Now applies to both the
  M3 memory file and Sonnet's new action log.

- **`delegate_task` input: a single raw natural-language `task` string, not structured fields.**
  Haiku just describes the job in plain language (e.g. "create a folder called Projects on the
  desktop"); Sonnet parses and plans it itself. Matches the existing philosophy of letting the
  model reason instead of forcing rigid categories (same reasoning as "tool use, not keyword
  matching" from the original trigger-mechanism decision).
- **Sonnet's system prompt: new file `jarvis_task_personality.txt`**, mirroring the existing
  `jarvis_personality.txt` pattern but for the task-executor persona. Tells Sonnet: you are
  Jarvis's task-execution arm with full CLI/filesystem access via `run_command`; given a task,
  plan it out, then execute; when done, write a detailed record of exactly what you did (task,
  commands run, output) to `Sonnet_Actions.md` before responding; then report the outcome back in
  simple, plain, spoken-friendly language.
- **`Jarvis_Talking.py` currently has no Sonnet call path at all.** `get_jarvis_response()` is the
  only function, and it always calls `claude-haiku-4-5` ([Jarvis_Talking.py:51](../Jarvis_Talking.py#L51)).
  This milestone adds a second function (e.g. `run_sonnet_task()`) making its own API call with
  `model="claude-sonnet-5"`, its own system prompt, and `run_command` bound to it — triggered only
  when Haiku's `delegate_task` fires.

## Progress as of end of session 2026-07-06 — READ THIS FIRST NEXT SESSION

Design is locked (rest of this doc above). Implementation started; below is the real state of
the code, which has diverged in naming/structure from the plan's suggested names — use the
actual names below, not the plan's placeholder names, when picking this back up.

**Bassam is writing the code himself (teach-don't-build mode).** Give skeletons/hints/isolated
examples, not finished implementations — he flagged mid-session that hints were creeping too
close to full solutions; keep him typing the actual logic. He got tired/frustrated near the end
of this session on the tool-use loop specifically (message list state, tool_use detection) — it's
genuinely the hardest mechanic in this milestone, go slow, one small piece at a time.

**Actual files so far (all in the repo root, not a subfolder):**
- `jarvis_cmd.py` — the real Task 1/3/4 file (plan called it `Jarvis_Task.py`). Contains:
  - `command_tool(command, working_directory=None)` — **done and tested, works.** This is the
    plan's `execute_run_command`. Runs via `["powershell", "-Command", command]` +
    `subprocess.run(..., cwd=working_directory, capture_output=True, text=True)`, returns
    `{"stdout":..., "stderr":..., "returncode":...}`. Correctly resolves `None` ->
    `os.getcwd()` inside the function body (not as a default-arg gotcha).
  - `jarvis_commands(task)` — this is the plan's `run_sonnet_task`. **In progress, not working
    yet.** Has: `system_prompt` read from `Jarvis_Tasking.txt`, client setup, `messages` seeded
    with `[{"role": "user", "content": task}]`, a `while True:` loop that calls
    `client.messages.create(...)` and appends the assistant response. **Missing:** the
    `RUN_COMMAND_TOOL` schema dict (referenced as `tools=[RUN_COMMAND_TOOL]` but not yet
    defined anywhere — this was never written, it's Task 1's other half), the tool_use detection
    loop (`for block in response.content: if block.type == "tool_use": ...`), the branch that
    calls `command_tool` and appends a `tool_result` message, the branch that returns the final
    text when there's no tool_use block, and the 20-call cap counter.
  - `jarvis_command_history()` — this is the plan's `read_sonnet_actions`. **Incomplete** — reads
    `C:\Users\kitan\Documents\Obsidian Vault\jarvis_memory\Jarvis_Commands.md` (note: this path,
    not `Sonnet_Actions.md` from the original plan — go with `Jarvis_Commands.md`, it's what's
    actually referenced in code) into a local `memory` variable but **never returns it** — needs
    a `return memory` line. The write half (`write_sonnet_action` in the plan) hasn't been
    started at all yet.
- `Jarvis_Tasking.txt` — this is the plan's `jarvis_task_personality.txt`, **done.** Written well;
  covers the task-executor persona, PowerShell usage, working_directory-must-be-passed-every-call
  caveat, the 20-operation cap, and the plain-spoken-final-answer requirement. No changes needed.

**Not started at all:** the `RUN_COMMAND_TOOL` schema dict, finishing `jarvis_commands`'s loop
body, `jarvis_command_history`'s missing return + its write counterpart, and all of Task 5/6
(wiring `delegate_task` into `Jarvis_Talking.py`, end-to-end test). Nothing has been committed to
git yet this session — first commit should happen once `command_tool` + the tool schema +
`jarvis_commands` loop are all working together.

**Suggested next step:** finish `RUN_COMMAND_TOOL` (shape given in Task 1 below, using the actual
name `command_tool` for the executor it maps to), then the tool_use-detection `for` loop inside
`jarvis_commands`, one small piece at a time — that's exactly where the session left off.

## Task reference (original plan — names below may differ from actual code above)
"Test" per task means running the relevant piece manually (a small script, or the real voice
loop), not an automated test suite — this repo has none.

## Implementation Plan

**File structure:**
- **Create `Jarvis_Task.py`** — everything Sonnet-side: the `run_command` tool schema, the
  executor that actually runs shell commands, the action-log read/write, and the
  `run_sonnet_task()` loop. One file, one responsibility: "the task-execution arm," mirroring how
  `Jarvis_Memory.py` is its own file for memory.
- **Create `jarvis_task_personality.txt`** — Sonnet's system prompt, sibling to
  `jarvis_personality.txt`.
- **Modify `Jarvis_Talking.py`** — add the `delegate_task` tool schema, pass it into
  `get_jarvis_response`'s `tools=` param, and handle the tool_use branch in `main()`'s loop.

### Task 1: `run_command` tool schema + executor (`Jarvis_Task.py`)

Define the Anthropic tool schema as a module-level dict, e.g.:

```python
RUN_COMMAND_TOOL = {
    "name": "run_command",
    "description": "...",  # you write this — tell Claude what it does and when to use it
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "..."},
            "working_directory": {"type": "string", "description": "..."}
        },
        "required": ["command"]  # working_directory optional — defaults per the design doc above
    }
}
```

Then write the executor:

```python
def execute_run_command(command, working_directory=None):
    """
    Runs `command` in a subprocess, in `working_directory` if given
    (default: this process's own cwd per the M4 doc).
    Returns a dict with at least: stdout, stderr, returncode.
    Hint: subprocess.run(..., shell=True, cwd=..., capture_output=True, text=True)
    """
```

- [ ] Write `RUN_COMMAND_TOOL` and `execute_run_command`.
- [ ] Manually test: at the bottom of `Jarvis_Task.py`, under `if __name__ == "__main__":`, call
  `execute_run_command("dir")` (or a command of your choice) and print the result. Run
  `python Jarvis_Task.py` and confirm you see real command output.
- [ ] Commit.

### Task 2: Sonnet's system prompt (`jarvis_task_personality.txt`)

Write the file. Per the decisions above, it must tell Sonnet:
- It is Jarvis's task-execution arm, with full CLI/filesystem access via `run_command`.
- Given a task, plan first, then execute — it can call `run_command` multiple times in sequence.
- Before giving its final answer, it must have a clear picture of exactly what it ran (this
  feeds Task 3's action log).
- Its final answer must be simple, plain, spoken-friendly language — no command-by-command
  narration, no technical jargon — since that final answer gets spoken aloud via `voice.Speak()`.

- [ ] Write `jarvis_task_personality.txt`.
- [ ] Commit.

### Task 3: Sonnet action log (`Jarvis_Task.py`)

```python
def read_sonnet_actions():
    """
    Reads C:\\Users\\kitan\\Documents\\Obsidian Vault\\jarvis_memory\\Sonnet_Actions.md
    and returns its raw text (empty string if the file doesn't exist yet — create it).
    """

def write_sonnet_action(task, commands_run, result):
    """
    Appends one entry to Sonnet_Actions.md: the task description, the list of
    (command, working_directory, output) actually run, and the final result.
    Include a timestamp (datetime.datetime.now()).
    """
```

- [ ] Write both functions. Keep the log format plain text/markdown — no need for the
  label-parsing dance `Jarvis_Memory.text_to_dict` does, since this file is read back as one raw
  blob of context, not turn-by-turn dicts.
- [ ] Manually test: call `write_sonnet_action(...)` with fake data, confirm the file gets
  created/appended correctly, then call `read_sonnet_actions()` and print it back.
- [ ] Commit.

### Task 4: `run_sonnet_task()` loop (`Jarvis_Task.py`)

```python
def run_sonnet_task(task):
    """
    Args: task (str) — the raw natural-language task Haiku wants done.
    Returns: (str) — Sonnet's final, spoken-friendly summary of what it did.

    Loop shape (per the M4 doc):
      1. Call client.messages.create(model="claude-sonnet-5", system=<jarvis_task_personality.txt>,
         tools=[RUN_COMMAND_TOOL], messages=<running list starting from `task` + read_sonnet_actions()
         as context>)
      2. If the response has a tool_use block: run execute_run_command with its input, append a
         tool_result message, track the (command, working_directory, output) for the log, go to 1.
      3. If the response is plain text: that's the final answer. Call write_sonnet_action(...),
         return the text.
      4. Cap at 20 iterations (per the M4 doc) — if hit without a plain-text answer, return a
         message saying the task got stuck, and still log what was attempted.
    """
```

- [ ] Implement it. Gotcha to watch for: Anthropic's tool-use API requires every assistant
  `tool_use` block to be followed by a matching `tool_result` in the *next* message before you
  call the API again — this is internal to this function's own message list, separate from the
  main `history` in `Jarvis_Talking.py` (which never sees Sonnet's raw tool calls at all, per the
  "one Jarvis" decision).
- [ ] Manually test: call `run_sonnet_task("create a folder called test_folder on the desktop")`
  directly (temporary code, or from a Python REPL) and confirm: the folder actually gets created,
  the function returns a plain-language summary, and `Sonnet_Actions.md` gets a new entry with
  the real command that ran.
- [ ] Commit.

### Task 5: Wire `delegate_task` into `Jarvis_Talking.py`

Add the tool schema (same file, near the top or next to `get_jarvis_response`):

```python
DELEGATE_TASK_TOOL = {
    "name": "delegate_task",
    "description": "...",  # tell Haiku when to use this: real system/file/command actions
    "input_schema": {
        "type": "object",
        "properties": {"task": {"type": "string", "description": "..."}},
        "required": ["task"]
    }
}
```

Modify `get_jarvis_response` ([Jarvis_Talking.py:43-55](../Jarvis_Talking.py#L43-L55)) to pass
`tools=[DELEGATE_TASK_TOOL]` into `client.messages.create(...)` and to return the **whole
response object**, not just `response.content[0].text` — the caller needs to inspect all content
blocks now, not just assume the first one is the final text.

In `main()`'s loop ([Jarvis_Talking.py:22-37](../Jarvis_Talking.py#L22-L37)), after calling
`get_jarvis_response`, check the response's content blocks:
- Collect any `text` blocks (the filler line) and speak them immediately if a `tool_use` block
  for `delegate_task` is also present.
- If a `delegate_task` tool_use block is present: call `Jarvis_Task.run_sonnet_task(task)` with
  its `task` input, get back Sonnet's summary, and combine the filler text + summary into the
  single string that gets spoken, appended to `history` as the assistant turn, and passed to
  `Jarvis_Memory.write_to_memory(...)` — exactly as if Jarvis (singular) had said it all itself.
- If there's no `tool_use` block, behave exactly as today: the text block is the whole answer.

- [ ] Import `Jarvis_Task` at the top of `Jarvis_Talking.py`.
- [ ] Make the changes above.
- [ ] Commit.

### Task 6: End-to-end manual test

- [ ] Run `python Jarvis_Talking.py` and, by voice, ask Jarvis to do something real — e.g. "create
  a folder called Milestone4Test on the desktop."
- [ ] Confirm: you hear a filler line, then Jarvis speaks a simple result, the folder actually
  exists, `Jarvis_Chat.md` has one new combined entry (not a trace of the handoff), and
  `Sonnet_Actions.md` has a new detailed entry with the real command run.
- [ ] Ask a follow-up in the same session referencing what just happened (e.g. "what's in that
  folder?") to confirm Haiku's `history` actually carries the memory of the task forward.
- [ ] Update this doc's "Not started" section to reflect what shipped, and note anything that
  came up during implementation that changes the design above.

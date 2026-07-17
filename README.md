# Jarvis

A personal AI assistant, built twice.

## Jarvis v1 vs Jarvis v2

The first time I built Jarvis, I vibe-coded the whole thing. I typed prompts at AI until something worked, and something did work — a chatbot that talked back. That was the first real lesson: AI is 1,000% helpful. It can build you almost anything, fast.

But it taught me something else too, the hard way. If you don't actually understand what's being written, you hit a wall you can't see coming. AI can hand you a lot of code, and if you don't know what any of it does, you have no way to tell good code from bad code until it breaks. At that point you're not debugging a project anymore — you're standing next to a pile of stuff that used to work, with no idea how to fix it. If you're not certain about what you're doing, you are horribly in a disaster.

Jarvis v2 is the redo, done right. This time I started with Jarvis teaching me instead of building for me — I write the code, I read the code, I explain the bug before it gets explained to me, and AI steps in as a second pair of eyes rather than the pair of hands. Only after I actually understand a piece do I let AI help integrate it or move faster. Every file in this repo, I can tell you what it does and why it's shaped that way. That difference — understanding versus output — is the whole difference between v1 and v2.

## What I actually learned about coding

I used to think coding was: open the terminal, open VS Code, start typing. That's not it. It turns out most of the actual work is everything around the typing — planning what you're about to build before you build it, reading code that already exists before you touch it, debugging patiently instead of guessing, and rewriting the same ten lines three times because the first two versions were wrong in ways you didn't see until you tried them. The typing is the easy part. The thinking is the job.

Building Jarvis this way — slower, more deliberate, actually understanding each piece — was a genuinely great experience. It was enjoyable in a way that vibe-coding v1 never was, because I could feel myself getting better at this instead of just getting a result.

## About this project

Jarvis is built incrementally across milestones, on Claude's API throughout:

1. **Terminal text chat** — the first working loop.
2. **Voice** — speech in, speech out.
3. **Persistent memory** — Jarvis remembers across sessions.
4. **Filesystem / shell control** — Jarvis can delegate real system tasks to a task-executing sub-agent.
5. **Vision + PC control** — Jarvis can see the screen and act on it (click, type).


See [`CLAUDE.md`](CLAUDE.md) for the full technical breakdown of every file, and [`teacher/`](teacher) for the milestone-by-milestone progress notes.

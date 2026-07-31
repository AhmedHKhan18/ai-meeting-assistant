---
id: 0011
title: Fix Discord channel name resolution
stage: green
date: 2026-07-31
surface: agent
model: claude-fable-5
feature: 001-meeting-workflow-automation
branch: 001-meeting-workflow-automation
user: ahmed.18hassan.18@gmail.com
command: direct-instruction
labels: ["discord", "bugfix", "notifications"]
links:
  spec: specs/001-meeting-workflow-automation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - tools/discord_tool.py
 - tests/unit/test_discord_tool.py
tests:
 - pytest tests/ (72 passed)
 - ruff check (all checks passed)
 - mypy tools/discord_tool.py tests/unit/test_discord_tool.py (no issues found)
---

## Prompt

now fix this "{"timestamp": "2026-07-31T15:59:58.709365+00:00", "level": "INFO", "agent": "discord_tool", "message": "discord_ready", "user": "Open Claw#3977"}
{"timestamp": "2026-07-31T16:03:00.144709+00:00", "level": "INFO", "agent": "transcript_agent", "message": "poll_transcripts", "workflow": "meeting_workflow", "event": "poll_transcripts", "status": "success", "duration_ms": 7038.561500026844, "error": null}
{"timestamp": "2026-07-31T16:03:06.706583+00:00", "level": "INFO", "agent": "meeting_intelligence_agent", "message": "analyze_transcript", "workflow": "meeting_workflow", "event": "analyze_transcript", "status": "success", "duration_ms": 6559.4149000244215, "error": null, "meeting_title": "Ahmed's Meeting Notes"}
{"timestamp": "2026-07-31T16:03:10.233016+00:00", "level": "ERROR", "agent": "meeting_workflow", "message": "process_meeting", "workflow": "meeting_workflow", "event": "process_meeting", "status": "failed", "duration_ms": 10087.656800053082, "error": "Channel not resolvable yet: general", "meeting_id": "1Np-crHIZouQ_w4jn-g724UiQBg"}
Job "CEOAgent._run_meeting_workflow_job (trigger: interval[0:03:00], next run at: 2026-07-31 21:05:53 PKT)" raised an exception
Traceback (most recent call last):
  File "D:\Coding\ai-meeting-assistant\.venv\Lib\site-packages\apscheduler\executors\base.py", line 181, in run_coroutine_job
    retval = await job.func(*job.args, **job.kwargs)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Coding\ai-meeting-assistant\agents\ceo_agent.py", line 187, in _run_meeting_workflow_job
    await self.meeting_workflow.run()
  File "D:\Coding\ai-meeting-assistant\workflows\meeting_pipeline.py", line 47, in run
    result = await self._process_meeting(meeting)
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Coding\ai-meeting-assistant\workflows\meeting_pipeline.py", line 93, in _process_meeting
    await self.notification_agent.send_meeting_summary(
    ...<3 lines>...
    )
  File "D:\Coding\ai-meeting-assistant\agents\notification_agent.py", line 72, in send_meeting_summary
    await self.discord_tool.send_message(channel, "\n".join(lines))
  File "D:\Coding\ai-meeting-assistant\tools\discord_tool.py", line 114, in send_message
    await async_retry_call(_send)
  File "D:\Coding\ai-meeting-assistant\tools\retry.py", line 56, in async_retry_call
    return await func()
           ^^^^^^^^^^^^
  File "D:\Coding\ai-meeting-assistant\tools\discord_tool.py", line 103, in _send
    raise RecoverableError(f"Channel not resolvable yet: {channel}")
tools.retry.RecoverableError: Channel not resolvable yet: general"

## Response snapshot

This log confirms the previous Otter MCP fix (PHR 0010) is fully working end-to-end:
`poll_transcripts` and `analyze_transcript` both succeeded, pulling and summarizing the
real "Ahmed's Meeting Notes" meeting. The new failure is downstream, in Discord delivery.

Root cause: `config/settings.json`'s `discord.channels` is `["general"]` — a channel
*name*, not a numeric ID. But `tools/discord_tool.py`'s `send_message()` only ever tried
`self.client.get_channel(int(channel))`, gated behind `channel.isdigit()`. Since
`"general".isdigit()` is always `False`, `channel_obj` was unconditionally `None` — the
code path that would resolve a channel by name never existed. Every retry (and every future
run) would fail identically; this wasn't transient.

Fix: added `DiscordTool._resolve_channel()`, which resolves a numeric-ID string via
`get_channel()` as before, but for a non-numeric string searches every guild the bot has
joined for a text channel matching that name (`discord.utils.get(guild.text_channels,
name=channel)`). `send_message()`'s retried closure now calls this instead of the
ID-only lookup — the existing retry/backoff behavior (for the case where the bot's guild
cache genuinely isn't populated yet right after startup) is preserved unchanged.

Added `tests/unit/test_discord_tool.py` (5 tests, new file — none existed for
`discord_tool.py` before): numeric-ID resolution, name resolution across multiple guilds,
name-not-found, and `send_message()`'s success/failure paths through the new resolver.
`discord.Client.guilds` is a read-only property (no setter), so tests replace `tool.client`
with a `MagicMock()` entirely rather than monkeypatching individual attributes on a real
`discord.Client` instance.

Fixed a resulting mypy error: `_resolve_channel`'s return type needed to match
`discord.Client.get_channel`'s real signature (`GuildChannel | Thread | PrivateChannel |
None`), not the narrower `GuildChannel | None` first written.

Full suite: 72/72 passing (was 67 — +5 new), ruff clean. mypy clean on both touched files;
one pre-existing, unrelated mypy error surfaced in `tests/e2e/test_sc006_zero_manual_steps.py`
(a `Meeting | None` union-attr gap, not touched by or related to this fix) — left as-is,
out of scope for this error report.

## Outcome

- ✅ Impact: Discord notification delivery now works when channels are configured by name (as config/settings.json does) rather than only by numeric ID — the `process_meeting` workflow step that was failing 100% of the time now succeeds.
- 🧪 Tests: 72/72 passing (5 new); ruff clean; mypy clean on touched files.
- 📁 Files: tools/discord_tool.py, tests/unit/test_discord_tool.py
- 🔁 Next prompts: user should re-run `python main.py` to confirm the meeting summary now actually posts to the #general Discord channel, then verify Trello card creation completes the pipeline.
- 🧠 Reflection: this is the second consecutive real bug (after PHR 0010's Otter tool names) found only by the user running the live system — config-driven channel *names* were never exercised by any existing test, since every prior Discord test used numeric IDs. Added the first dedicated unit test file for discord_tool.py to close that gap.

## Evaluation notes (flywheel)

- Failure modes observed: a code path (name-based channel lookup) implied by config schema (`config/settings.json` ships a channel name, not an ID) was never implemented — config and code silently diverged with no test catching it.
- Graders run and results (PASS/FAIL): pytest PASS (72/72), ruff PASS, mypy PASS (scoped to touched files).
- Prompt variant (if applicable): n/a
- Next experiment (smallest change to try): consider fixing the pre-existing unrelated mypy gap in tests/e2e/test_sc006_zero_manual_steps.py:96 in a future pass (add a None-check/assert after get_meeting()).

---
id: 0008
title: Regenerate tasks for MCP migration delta
stage: tasks
date: 2026-07-31
surface: agent
model: claude-fable-5
feature: 001-meeting-workflow-automation
branch: 001-meeting-workflow-automation
user: ahmed.18hassan.18@gmail.com
command: /sp.tasks
labels: [tasks, regeneration, mcp, migration-delta]
links:
  spec: specs/001-meeting-workflow-automation/spec.md
  ticket: null
  adr: null
  pr: null
files:
 - specs/001-meeting-workflow-automation/tasks.md
tests:
 - none (task planning only)
---

## Prompt

(empty — `/sp.tasks` invoked with no arguments, regenerating `tasks.md` against the
MCP-revised `plan.md` from the prior `/sp.plan` re-run)

## Response snapshot

Ran `check-prerequisites.ps1 -Json` (research.md, data-model.md, contracts/,
quickstart.md all present) and re-read the existing 71-task `tasks.md` in full — it
already reflected a completed, fully-tested implementation (PHR
`0006-full-implementation-71-tasks`) built against the *prior* plan, now superseded by
the MCP architecture revision (PHR `0007-mcp-architecture-revision`).

Judgment call: rather than blindly regenerating a fresh 71-task list from scratch (which
would misrepresent reality — most of the codebase already exists and works, only the
Otter integration needs to change), treated this as a delta regeneration. Kept all 71
original tasks and their `[X]` status intact (accurate history — they were completed and
the code they describe still exists and passes tests, except where superseded), and
appended 13 new tasks (T072-T084) covering exactly the gap between the current codebase
and the revised plan:

- **T072-T077** (sequential chain): add MCP/OAuth dependencies → `OtterCredentials`
  model → `mcp/otter_client.py` → OAuth device-flow + refresh → update
  `agents/transcript_agent.py`'s two call sites → delete the now-unused
  `tools/otter_tool.py`.
- **T078-T079**: the plan's file renames (`workflows/*_workflow.py` → `*_pipeline.py`,
  `prompts/meeting_summary.md` → `summary.md`).
- **T080-T082**: replace/update the tests that exercised the old direct-REST client, plus
  a new OAuth-refresh-failure test.
- **T083-T084** (independent of the above): the two remaining renames scoped to User
  Story 4 (`morning_report.py`/`evening_report.py` → `*_pipeline.py`,
  `config/report_schedule.json` → `schedule.json`).

Annotated (not deleted or silently left as-is) the two tasks the migration makes
obsolete: T028 (`tools/otter_tool.py`) and T070 (its test) both stay `[X]` — they were
genuinely completed — but now carry a `**SUPERSEDED by T0xx**` note pointing to their
replacement, so a top-to-bottom read doesn't mistake them for still-current work.
Updated the Dependencies, Parallel Example, and Implementation Strategy sections to
cover the new tasks' ordering (T073→T074→T075→T076→T077→T082 is a strict chain; T072,
T078, T079, T083, T084 are independent and parallelizable with everything).

## Outcome

- ✅ Impact: `tasks.md` now accurately reflects both what's done (71 tasks, working,
  tested) and exactly what remains to bring the codebase in sync with the MCP-revised
  plan (13 new tasks, format-validated: sequential IDs T072-T084, correct `[P]`/`[US2]`/
  `[US4]` markers, every task has a file path).
- 🧪 Tests: None — planning output. The new tasks themselves define test work
  (T080, T081, T082) for a future `/sp.implement` pass.
- 📁 Files: `specs/001-meeting-workflow-automation/tasks.md` (append + 2 annotations).
- 🔁 Next prompts: `/sp.implement` to execute T072-T084 (the only remaining pending
  work) and migrate the codebase to match the revised plan; or, if the MCP architecture
  was exploratory rather than committed, the user may choose not to run it and leave
  `tasks.md` as an accurate record of the gap without acting on it yet.
- 🧠 Reflection: Standard `/sp.tasks` generation assumes a greenfield feature; this
  session is the first time it ran against a feature with substantial *existing,
  passing* work built against a now-superseded plan. Treating it as delta generation
  (append + annotate, don't rewrite history) rather than fresh generation preserved
  traceability and avoided producing a task list that would mislead a reader into
  re-doing already-correct work.

## Evaluation notes (flywheel)

- Failure modes observed: none in tooling this pass — `check-prerequisites.ps1` ran
  cleanly.
- Graders run and results (PASS/FAIL): Format validation — all 13 new tasks confirmed
  via grep to be sequential (T072-T084), checkbox-prefixed, with correct `[Story]`
  labels (US2 for T072-T082, US4 for T083-T084) and file paths. Total: 71 `[X]` + 13
  `[ ]` = 84 tasks. PASS.
- Prompt variant (if applicable): N/A
- Next experiment (smallest change to try): if a third architecture revision happens on
  this feature, this delta-regeneration pattern (append numbered tasks, annotate
  superseded ones with a forward pointer, update Dependencies/Parallel sections rather
  than rewriting them) held up well and is worth reusing rather than re-deriving from
  scratch each time.

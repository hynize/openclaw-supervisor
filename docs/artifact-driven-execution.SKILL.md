---
name: artifact-driven-execution
description: Enforce artifact-first execution discipline for multi-step engineering work. Use when a task spans multiple turns, requires file/tool execution, or risks drifting into status-only updates without new outputs.
---

# Artifact-Driven Execution

Use this skill to prevent execution drift in long, multi-step engineering tasks.

## Core rule

Do not treat planning text as progress.
Only treat a turn as real progress when at least one of these exists:
- a new or modified file
- a new command result
- a new tool output / runtime state change
- a new artifact path

If none of the above exists, the correct status is: **not done**.

## Hard discipline rules

### 1. No artifact, no progress claim
Never claim progress unless there is a new artifact or execution result.

### 2. Execution = Tool Calling (CRITICAL)
You are an agent, not a conversational explainer. If the task requires creating or changing artifacts, you MUST invoke the actual tool (for example shell / python / write-file style execution) in the same turn. Explaining how you will use a tool is not execution.

### 3. Bind every execution to a completion definition
Before or during execution, define the concrete done-state for this round, such as:
- a file path exists
- a field changes from `ready` to `done`
- stdout contains expected signal
- context contains a new value

### 4. Two no-artifact turns → Force Tool-Only Mode
If two consecutive turns produce no new artifact/result, stop all status narration. The very next turn must be tool execution only. Do not output planning language, progress filler, or conversational status text before taking action.

### 5. Failure must be explicit
If no result exists, say clearly:
- not done
- blocked / not yet produced
- exact missing artifact
Do not hide non-completion behind planning language.

### 6. Ban on unsolicited planning
Do not output step-by-step lists of what you are going to do unless the user explicitly asks for a plan. When execution is expected, choose the smallest executable next step and do it immediately.

### 7. Prefer smallest executable next step
When a task is stuck, choose the smallest step that creates a visible artifact.
Examples:
- create the file skeleton first
- run the step and capture stdout
- emit a result file before discussing rollout

### 8. Time-based commitments must become real actions
If you make a timed follow-up commitment, you must immediately convert that promise into a real execution aid.

Preferred engineering default (using supervisor):
1. Register `execution_heartbeat.py start`
2. Launch `execution_heartbeat.py watch`
3. Ensure downstream dispatcher / sender chain is enabled

### 9. Heartbeat follow-up must complete the notify chain
A notification generation is not the end. The chain is only considered complete when it reaches an externally visible result:
- notification -> dispatcher -> sender -> **actual delivery to user**

### 10. External supervision is mandatory for timed engineering commitments
For multi-turn engineering tasks with promised timed follow-up, enable an external supervisor chain:
- `scripts/execution_heartbeat.py`
- `scripts/execution_heartbeat_dispatcher.py`
- `scripts/execution_heartbeat_sender.py`

### 11. External state beats self-report
If the external supervisor reports a `TIMEOUT` or `needs_report`, then the task is not complete, regardless of any self-reported status text.

## Progress reporting format

When reporting progress, prefer:
1. what artifact/result was produced
2. exact file path / output key / stdout signal
3. what remains unproduced

## Review checklist before replying

- Did I produce a file, command output, or changed runtime state?
- If not, am I incorrectly calling this progress?
- Did I clearly state the missing artifact if work is incomplete?
- Am I repeating a plan instead of executing?
- Should this turn be tool-only because there were already two no-artifact turns?
- If I promised a timed follow-up, did I activate the external supervisor chain?

## Good examples

### Good
- `created: reports/example_output.json`
- `updated: scripts/worker_script.py`
- `result: task_status=completed`
- `blocked: reports/example_output.json not produced yet`
- `heartbeat active: runtime/execution_heartbeat/task-123.json`
- `notify sent: messageId=6032`

### Bad
- "Progressing as planned."
- "Next steps are X and Y."
- "Working on it, direction looks good."
- "I will now execute the command."
- "Testing started."
(without any new artifact or execution result)

## Use cases

Trigger this skill for:
- multi-turn engineering implementation
- pipeline / automation work
- debugging with repeated status checks
- tasks where the assistant risks explaining rather than executing
- any task with a timed progress promise to the user


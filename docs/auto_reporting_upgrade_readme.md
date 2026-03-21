# Automated Reporting Module: Overview and Architecture

## Objective
To transition periodic task reporting from manual updates to an observable, auditable, and automatically triggered engineering loop. The system ensures that project status reports are generated and delivered proactively upon task completion or deadline expiration.

## Core Components

### 1. Heartbeat Layer (`scripts/execution_heartbeat.py`)
- **Functions**: `start`, `check`, `watch`, `alarm`, `notify`.
- Acts as the primary state machine for task monitoring and deadline enforcement.

### 2. Dispatcher & Outbox Layer (`scripts/execution_heartbeat_dispatcher.py`)
- **Purpose**: Converts notifications into deliverable message payloads.
- **Directory Structure**:
  - `runtime/execution_heartbeat/outbox/ready_to_send/`
  - `runtime/execution_heartbeat/outbox/processing/`
  - `runtime/execution_heartbeat/outbox/sent/`
  - `runtime/execution_heartbeat/outbox/failed/`

### 3. Sender Layer (`scripts/execution_heartbeat_sender.py`)
- Consumes the outbox and performs actual message delivery via the unified message interface.
- Includes retry logic and status logging.

### 4. Status Reporting Layer
- **Status Store**: `runtime/project_status.json` (or `.example.json` for templates).
- **Interface**: `scripts/update_project_status.py`.
- **Generator**: `scripts/status_report_generator.py` (renders human-readable reports from JSON data).

### 5. Automation Layer (`scripts/message_consumer.sh`)
- A background process that polls the dispatcher and sender to ensure continuous delivery.

## Key Principles & Lessons Learned
1. **Artifact-Driven Progress**: Valid progress is defined by the production of artifacts (files, command outputs), not by status updates alone.
2. **Mechanized Commitments**: Timed promises must be backed by automated heartbeat and alarm mechanisms.
3. **Single Source of Truth**: `project_status.json` serves as the authoritative state for all automated reporting.
4. **Content-Rich Reporting**: Automated reports should convey actual state and artifacts, rather than just simple reminders.
5. **End-to-End Verification**: A task is only "done" when the user confirms receipt of the final status message.

## Current Maturity
- The full "Watch -> Alarm -> Notify -> Dispatch -> Send" loop is verified and stable.
- The system is integrated into documentation and developer skills as a standard for long-running tasks.


# System Architecture

## Core Components

The OpenClaw Supervisor is built on a layered architecture to ensure both process reliability and task-level visibility.

### 1. Process Supervision Layer (`supervisor.py`)
- **Lifecycle Management**: Starts, stops, and restarts target processes.
- **Resource Tracking**: Monitors PID-specific CPU and memory consumption.
- **Auto-Healing**: Triggers restarts based on exit code or liveness probes.

### 2. Heartbeat & State Machine Layer (`scripts/execution_heartbeat.py`)
- **Task Registration**: Defines deadlines and expected artifacts for specific task IDs.
- **Watchdog**: Periodically checks for task liveness and deadline status.
- **Alarm/Notify**: Generates alerts when tasks miss deadlines or fail.

### 3. Messaging & Reporting Layer
- **Dispatcher (`execution_heartbeat_dispatcher.py`)**: Batches heartbeat notifications into structured state reports.
- **Outbox System**: Buffers outgoing messages in `runtime/execution_heartbeat/outbox/` to handle intermittent network issues.
- **Sender (`execution_heartbeat_sender.py`)**: Performs actual message delivery (e.g., via Telegram or Webhooks) with built-in retry logic.
- **Status Generator (`status_report_generator.py`)**: Renders human-readable summaries from the central `project_status.json`.

## Data Flow
1. **Task Events** -> `execution_heartbeat` (Updates local state)
2. **Scan/Check** -> `execution_heartbeat` (Detects deadline breach) -> `Notify` event
3. **Notify** -> `Dispatcher` (Aggregates) -> `Outbox` (Writes JSON files)
4. **Outbox Consumer** -> `Sender` (Attempts delivery) -> `Success/Failure` logging

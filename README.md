# OpenClaw Supervisor

A robust supervision and automated reporting component designed for long-running AI agents and automation tasks.

## Key Features

- **Process Supervision & Auto-Restart**: Monitors specified process PIDs and automatically restarts them if they crash or exit unexpectedly.
- **Resource Monitoring**: Provides visibility into CPU and memory usage for monitored processes.
- **Automated Status Reporting**: Synchronizes project status and automatically generates reports based on deadllines.
- **Outbox & Retry Mechanism**: Ensures reliable message delivery via an asynchronous outbox and heartbeat system.
- **Alert Aggregation**: Batches multiple alerts to prevent notification fatigue.

---

## 🏗️ Architecture

The system consists of two main layers:
1. **Core Supervisor (`supervisor.py`)**: High-level process monitoring, resource tracking, and lifecycle management.
2. **Heartbeat & Reporting (`scripts/`)**: Task-level deadline tracking, artifact verification, and status synchronization.

---

## 🛠️ Installation

```bash
git clone https://github.com/hynize/openclaw-supervisor.git
cd openclaw-supervisor
```
Uses Python standard libraries only. No external dependencies required for core functionality.

---

## 🚀 Quick Start

### 1. Process Protection
Monitor a process and restart it automatically if it fails:
```bash
python supervisor.py start \
  --task-id "demo-task-01" \
  --deadline-min 60 \
  --pid 1234 \
  --command "python agent.py" \
  --auto-restart
```

### 2. Task Deadlines & Automated Reporting
Register a task that expects an output file within a specific timeframe:
```bash
# Register a heartbeat task
python scripts/execution_heartbeat.py start \
  --task-id "sync-task" \
  --deadline-min 30 \
  --expect-file "output/report.md"

# Update project status for the automated report
python scripts/update_project_status.py \
  --set-focus "feature-development" \
  --add-incomplete "task-alpha"
```

### 3. Enable Background Consumer
Start the asynchronous message consumer to handle outbox delivery:
```bash
nohup bash scripts/message_consumer.sh &
```

---

## 📂 Components

- `scripts/execution_heartbeat.py`: State machine for task deadlines and artifact collection.
- `scripts/execution_heartbeat_dispatcher.py`: Aggregates and dispatches alerts.
- `scripts/execution_heartbeat_sender.py`: Handles message delivery with retry logic.
- `scripts/update_project_status.py`: Interface for updating the global project status.
- `runtime/project_status.example.json`: Template for project status tracking.

## Use Cases
Ideal for developers running long-term automation scripts, web crawlers, or AI-driven agents that require high availability and structured progress updates.


# Heartbeat and Automated Reporting: Failure Mode Analysis

This document analyzes the reliability of the "artifact-driven heartbeat supervision + automated status reporting" cycle, focusing on edge cases, extreme failures, and common omissions.

## 5 Identified Vulnerabilities

### 1. Watcher Process Liveness
**Scenario**: A task is registered with a `watch` interval, but the watcher process itself is killed (e.g., host reboot, OOM, or parent process termination).
**Issue**: The task becomes an "orphan." Since the watcher is dead, no check will be performed, and the deadline will pass without triggering any alarms or notifications.
**Mitigation**: Implement a global background scanner (within the message consumer or a cron job) that periodically sweeps all `PENDING` task JSONs and triggers a `check` operation.

### 2. Status Report Desynchronization
**Scenario**: A task successfully produces the expected artifact before the deadline. The heartbeat system marks it as `SUCCESS`. However, the developer or agent forgets to update the global `project_status.json`.
**Issue**: The automated report generated from `project_status.json` will still show the task as "Incomplete," leading to confusion.
**Mitigation**: Introduce a post-success hook in the heartbeat system to automatically transition items from `incomplete` to `completed` in `project_status.json`.

### 3. Reliable Message Delivery (Outbox Retries)
**Scenario**: A notification is generated in the `outbox/ready_to_send/` directory. The sender attempts to deliver it but fails due to network issues or API downtime.
**Issue**: Without a retry mechanism, the message is moved to `failed/` and never sent, leaving the user without critical updates.
**Mitigation**: Implement an exponential backoff retry mechanism in the sender that periodically re-attempts delivery for messages in the `failed/` directory until a threshold is reached.

### 4. Recovery from Timeout (Late Success)
**Scenario**: A task misses its deadline and is marked as `TIMEOUT`. Later, the artifact is finally produced.
**Issue**: The state machine remains locked in `TIMEOUT`. The user is not notified that the late artifact has arrived.
**Mitigation**: Allow the state machine to transition from `TIMEOUT` to a `LATE_SUCCESS` state if the artifact is detected in subsequent checks, triggering a "recovery" notification.

### 5. Notification Fatigue (Message Storms)
**Scenario**: Multiple tasks are scheduled with the same deadline. If they all fail simultaneously, the dispatcher sends multiple individual reports.
**Issue**: The user receives a flood of near-identical messages in a short window.
**Mitigation**: Implement a debouncing or batching mechanism in the dispatcher. If multiple notifications arrive within a small window, they should be aggregated into a single summary report.

## Summary
The current implementation serves as a functional MVP for contract-based supervision. To reach production-grade reliability, the system must evolve to include self-healing capabilities, primarily focusing on reliable delivery retries and proactive background scanning.


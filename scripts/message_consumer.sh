#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Ensure logs directory exists to prevent redirection failure
mkdir -p "$PROJECT_ROOT/logs"

while true; do
  python3 scripts/execution_heartbeat.py check_all >"$PROJECT_ROOT/logs/message_consumer_check_all.log" 2>&1 || true
  python3 scripts/execution_heartbeat_dispatcher.py >"$PROJECT_ROOT/logs/message_consumer_dispatch.log" 2>&1 || true
  python3 scripts/execution_heartbeat_sender.py >"$PROJECT_ROOT/logs/message_consumer_sender.log" 2>&1 || true
  sleep 10
done

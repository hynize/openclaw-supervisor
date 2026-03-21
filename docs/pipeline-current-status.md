# Current Status

## Fully working
- Contract-first promote path
- Graded linter
- Compare summary and field compare
- Baseline registry and promotion log
- Formal PDF delivery path

## Current stable runtime outputs
- `generation_action = generated_now`
- `delivery_action = formal_sent`

## Review focus
1. Whether the current version remains the right baseline pointer
2. Whether the working section-ready input remains valid
3. Whether build_section_ready should become the canonical generation entry
4. Whether DeliveryStep should later own full render + send end-to-end


## Auto-reporting status (2026-03-20)
### Fully working
- `execution_heartbeat.py` supports `start/check/watch/alarm/notify`
- `execution_heartbeat_dispatcher.py` converts notify into state-report messages
- `execution_heartbeat_sender.py` consumes `ready_to_send -> processing -> sent/failed`
- `status_report_generator.py` renders message text from `runtime/project_status.json`
- 1-minute automatic project status reporting test completed successfully

### Stable artifacts
- `runtime/project_status.json`
- `runtime/execution_heartbeat/*.json`
- `runtime/execution_heartbeat/outbox/ready_to_send/`
- `runtime/execution_heartbeat/outbox/sent/`
- `runtime/execution_heartbeat/dispatcher_delivery_log.jsonl`

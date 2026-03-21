#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
RUNTIME_DIR = PROJECT_ROOT / 'runtime' / 'execution_heartbeat'
OUTBOX_DIR = RUNTIME_DIR / 'outbox'
READY_DIR = OUTBOX_DIR / 'ready_to_send'
PROCESSING_DIR = OUTBOX_DIR / 'processing'
SENT_DIR = OUTBOX_DIR / 'sent'
FAILED_DIR = OUTBOX_DIR / 'failed'
for d in [READY_DIR, PROCESSING_DIR, SENT_DIR, FAILED_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def load_notify_files():
    return sorted(RUNTIME_DIR.glob('*.notify.json'))


def build_message_body(events_str: str, checked_at: str):
    result = subprocess.run(
        ['python3', str(SCRIPT_DIR / 'status_report_generator.py')],
        capture_output=True,
        text=True,
    )
    report = result.stdout.strip() if result.returncode == 0 else f"⚠️ 状态汇报生成失败: {result.stderr.strip()}"
    return (
        f"{report}\n\n"
        f"🔔 批量心跳事件：\n{events_str}\n"
        f"🕒 检查时间：{checked_at}"
    )


def dispatch_only():
    dispatched = []
    notify_files = load_notify_files()
    if not notify_files:
        return

    valid_events = []
    for nf in notify_files:
        data = json.loads(nf.read_text(encoding='utf-8'))
        if not data.get('needs_report'):
            ignored = nf.with_name(nf.name.replace('.notify.json', '.ignored.json'))
            nf.rename(ignored)
            continue
        valid_events.append((data, nf))

    if not valid_events:
        return

    batch_checked_at = datetime.now(timezone.utc).isoformat().replace(':', '-').replace('+', '_')
    batch_timestamp_display = datetime.now(timezone.utc).isoformat()
    
    events_msg_lines = []
    for data, nf in valid_events:
        # data may contain predefined complete text formatting
        msg_override = data.get('message', f"任务 [{data.get('task_id', 'unknown')}] 状态: {data.get('status', 'unknown')}")
        events_msg_lines.append(f"- {msg_override}")
    
    events_str = "\n".join(events_msg_lines)
    
    ready_path = READY_DIR / f'batch_{batch_checked_at}.json'
    payload = {
        'task_id': 'batch_alarm',
        'message': build_message_body(events_str, batch_timestamp_display),
        'status': 'BATCH',
        'checked_at': batch_timestamp_display
    }
    
    ready_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    
    # Mark all valid_events as notified
    for data, nf in valid_events:
        notified = nf.with_name(nf.name.replace('.notify.json', '.notified.json'))
        nf.rename(notified)
        dispatched.append({'source': str(nf), 'notified_marker': str(notified)})
        
    print(json.dumps({'batch_dispatched': str(ready_path), 'items': dispatched}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    dispatch_only()

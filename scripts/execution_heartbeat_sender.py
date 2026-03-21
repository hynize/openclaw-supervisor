#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
RUNTIME_DIR = PROJECT_ROOT / 'runtime' / 'execution_heartbeat'
BASE_OUTBOX = RUNTIME_DIR / 'outbox'
READY_DIR = BASE_OUTBOX / 'ready_to_send'
PROCESSING_DIR = BASE_OUTBOX / 'processing'
SENT_DIR = BASE_OUTBOX / 'sent'
FAILED_DIR = BASE_OUTBOX / 'failed'
DELIVERY_LOG = RUNTIME_DIR / 'dispatcher_delivery_log.jsonl'

for d in [READY_DIR, PROCESSING_DIR, SENT_DIR, FAILED_DIR]:
    d.mkdir(parents=True, exist_ok=True)


def log_event(payload: dict):
    with DELIVERY_LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps(payload, ensure_ascii=False) + '\n')


def sweep_failed():
    for p in sorted(FAILED_DIR.glob('*.json')):
        try:
            payload = json.loads(p.read_text(encoding='utf-8'))
            retry_count = payload.get('retry_count', 0)
            if retry_count < 3:
                payload['retry_count'] = retry_count + 1
                ready_path = READY_DIR / p.name
                ready_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
                p.unlink()
        except Exception:
            pass


def process_ready():
    moved = []
    
    # 1. Sweep failed folder first to recover items for sending
    sweep_failed()
    
    # 2. Process ready folder
    for p in sorted(READY_DIR.glob('*.json')):
        processing = PROCESSING_DIR / p.name
        sent = SENT_DIR / p.name
        failed = FAILED_DIR / p.name
        try:
            os.rename(p, processing)
        except FileNotFoundError:
            continue

        payload = json.loads(processing.read_text(encoding='utf-8'))
        message = payload.get('message', '')
        cmd = [
            'openclaw', 'message', 'send',
            '--channel', 'telegram',
            '--target', '1797428566',
            '--message', message,
            '--silent', '--json'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and '"ok": true' in result.stdout:
            os.rename(processing, sent)
            log_event({
                'task_id': payload.get('task_id'),
                'status': 'sent',
                'sent_file': str(sent),
                'stdout': result.stdout.strip(),
                'retry_count': payload.get('retry_count', 0)
            })
            moved.append({'source': str(p), 'sent': str(sent), 'task_id': payload.get('task_id'), 'status': 'sent'})
        else:
            os.rename(processing, failed)
            log_event({
                'task_id': payload.get('task_id'),
                'status': 'failed',
                'failed_file': str(failed),
                'stdout': result.stdout.strip(),
                'stderr': result.stderr.strip(),
                'retry_count': payload.get('retry_count', 0)
            })
            moved.append({'source': str(p), 'failed': str(failed), 'task_id': payload.get('task_id'), 'status': 'failed'})
    print(json.dumps({'moved': moved}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    process_ready()

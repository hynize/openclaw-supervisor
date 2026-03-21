#!/usr/bin/env python3
import argparse
import json
import time
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import update_project_status

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
RUNTIME_DIR = PROJECT_ROOT / 'runtime' / 'execution_heartbeat'
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()


def parse_iso(s):
    return datetime.fromisoformat(s)


@dataclass
class TaskSpec:
    task_id: str
    created_at: str
    deadline_at: str
    expected_files: list
    status: str = 'PENDING'
    results: dict = None


def task_path(task_id: str) -> Path:
    return RUNTIME_DIR / f'{task_id}.json'


def history_path() -> Path:
    return RUNTIME_DIR / 'history.jsonl'


def alarm_path(task_id: str) -> Path:
    return RUNTIME_DIR / f'{task_id}.alarm.json'


def load_task(task_id: str) -> dict:
    p = task_path(task_id)
    if not p.exists():
        raise FileNotFoundError(f'task not found: {task_id}')
    return json.loads(p.read_text(encoding='utf-8'))


def save_task(task: dict):
    task_path(task['task_id']).write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding='utf-8')


def append_history(event: dict):
    with history_path().open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')


def mark_project_files_completed(files):
    if not files: return
    try:
        data = update_project_status.load_status()
        for f in files:
            data['completed_items'].append(f)
        data['completed_items'] = update_project_status.dedup_keep_latest(data['completed_items'])
        data['incomplete_items'] = [x for x in data['incomplete_items'] if x not in set(files)]
        update_project_status.save_status(data)
    except Exception as e:
        print(f"Failed to auto-update project status: {e}", file=sys.stderr)


def write_alarm(task: dict, status: str):
    checked = iso(now_utc())
    # Both TIMEOUTs and LATE_SUCCESS need reports
    needs_report = status in ('TIMEOUT_NO_ARTIFACT', 'TIMEOUT_PARTIAL', 'LATE_SUCCESS')
    alarm = {
        'task_id': task['task_id'],
        'status': status,
        'needs_report': needs_report,
        'checked_at': checked
    }
    alarm_path(task['task_id']).write_text(json.dumps(alarm, ensure_ascii=False, indent=2), encoding='utf-8')
    
    if status == 'LATE_SUCCESS':
        message = f"🟢 [恢复正常] 任务 {task['task_id']} 曾超时但现已补齐产物。相关项已自动移入 completed_items。"
    else:
        message = f"⚠️ 任务 {task['task_id']} 到时状态为 {status}，请立即检查并汇报进度。"
        
    notify = {
        'task_id': task['task_id'],
        'kind': 'execution_heartbeat',
        'status': status,
        'needs_report': needs_report,
        'message': message,
        'checked_at': checked
    }
    (RUNTIME_DIR / f"{task['task_id']}.notify.json").write_text(json.dumps(notify, ensure_ascii=False, indent=2), encoding='utf-8')


def cmd_start(args):
    if not args.expect_file:
        raise ValueError('At least one --expect-file is required')
    created = now_utc()
    deadline = created + timedelta(minutes=args.deadline_min)
    expected_files = [str(Path(fp).resolve()) for fp in (args.expect_file or [])]
    task = asdict(TaskSpec(
        task_id=args.task_id,
        created_at=iso(created),
        deadline_at=iso(deadline),
        expected_files=expected_files,
        results={'raw_expected_files': args.expect_file or []}
    ))
    save_task(task)
    append_history({'event': 'START', 'task_id': args.task_id, 'created_at': task['created_at'], 'deadline_at': task['deadline_at']})
    print(task_path(args.task_id))
    print(json.dumps(task, ensure_ascii=False, indent=2))


def inspect_files(task: dict):
    created = parse_iso(task['created_at'])
    checks = []
    any_artifact = False
    all_ok = True
    for fp in task.get('expected_files', []):
        p = Path(fp)
        exists = p.exists()
        mtime_ok = False
        size_ok = False
        size = p.stat().st_size if exists else 0
        if exists:
            mtime = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
            mtime_ok = mtime >= created
            size_ok = size > 0
        ok = exists and mtime_ok and size_ok
        if exists and mtime_ok:
            any_artifact = True
        if not ok:
            all_ok = False
        checks.append({'path': fp, 'exists': exists, 'mtime_ok': mtime_ok, 'size_ok': size_ok, 'size': size, 'ok': ok})
    return checks, any_artifact, all_ok


def evaluate(task: dict):
    checks, any_artifact, all_ok = inspect_files(task)
    deadline = parse_iso(task['deadline_at'])
    now = now_utc()
    old_status = task.get('status', 'PENDING')
    
    if all_ok and task['expected_files']:
        new_status = 'LATE_SUCCESS' if old_status in ('TIMEOUT_NO_ARTIFACT', 'TIMEOUT_PARTIAL') else 'SUCCESS'
    elif now >= deadline and not any_artifact:
        new_status = 'TIMEOUT_NO_ARTIFACT'
    elif now >= deadline and any_artifact:
        new_status = 'TIMEOUT_PARTIAL'
    else:
        new_status = 'PENDING'
        
    task['status'] = new_status
    if not task.get('results'):
        task['results'] = {}
    task['results']['files'] = checks
    task['results']['checked_at'] = iso(now)
    
    status_changed = (old_status != new_status)
    return task, status_changed


def handle_evaluation_result(task: dict, status_changed: bool):
    save_task(task)
    if status_changed:
        append_history({'event': 'STATUS_CHANGE', 'task_id': task['task_id'], 'status': task['status'], 'checked_at': task['results']['checked_at']})
        
        if task['status'] in ('SUCCESS', 'LATE_SUCCESS'):
            raw_files = task.get('results', {}).get('raw_expected_files', task.get('expected_files', []))
            mark_project_files_completed(raw_files)
            
        if task['status'] in ('TIMEOUT_NO_ARTIFACT', 'TIMEOUT_PARTIAL', 'LATE_SUCCESS'):
            write_alarm(task, task['status'])


def do_check_task(task_id: str):
    task = load_task(task_id)
    if task.get('status') in ['SUCCESS', 'LATE_SUCCESS']:
        # Terminal states, no further checks needed.
        return task
        
    task, status_changed = evaluate(task)
    handle_evaluation_result(task, status_changed)
    return task


def cmd_check(args):
    task = do_check_task(args.task_id)
    print(json.dumps(task, ensure_ascii=False, indent=2))


def cmd_check_all(args):
    checked = []
    for p in sorted(RUNTIME_DIR.glob('*.json')):
        if p.name.endswith('.alarm.json') or p.name.endswith('.notify.json'):
            continue
        try:
            task_data = json.loads(p.read_text(encoding='utf-8'))
            if task_data.get('status') not in ['SUCCESS', 'LATE_SUCCESS']:
                do_check_task(task_data['task_id'])
                checked.append(task_data['task_id'])
        except Exception as e:
            print(f"Failed to check {p.name}: {e}", file=sys.stderr)
    print(json.dumps({"checked_tasks": checked}, ensure_ascii=False, indent=2))


def cmd_watch(args):
    while True:
        task = do_check_task(args.task_id)
        if task.get('status') in ['SUCCESS', 'LATE_SUCCESS', 'TIMEOUT_NO_ARTIFACT', 'TIMEOUT_PARTIAL']:
            # For watch loop, we exit on any final state or timeout, just like before, 
            # but rely on check-all background scan to handle transition to LATE_SUCCESS later.
            print(json.dumps(task, ensure_ascii=False, indent=2))
            return
        time.sleep(args.interval_sec)


def cmd_list(args):
    items = []
    for p in sorted(RUNTIME_DIR.glob('*.json')):
        if p.name.endswith('.alarm.json') or p.name.endswith('.notify.json'):
            continue
        items.append(json.loads(p.read_text(encoding='utf-8')))
    print(json.dumps(items, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='cmd', required=True)

    p1 = sub.add_parser('start')
    p1.add_argument('--task-id', required=True)
    p1.add_argument('--deadline-min', type=int, required=True)
    p1.add_argument('--expect-file', action='append')
    p1.set_defaults(func=cmd_start)

    p2 = sub.add_parser('check')
    p2.add_argument('--task-id', required=True)
    p2.set_defaults(func=cmd_check)

    p2_all = sub.add_parser('check_all')
    p2_all.set_defaults(func=cmd_check_all)

    p3 = sub.add_parser('watch')
    p3.add_argument('--task-id', required=True)
    p3.add_argument('--interval-sec', type=int, default=30)
    p3.set_defaults(func=cmd_watch)

    p4 = sub.add_parser('list')
    p4.set_defaults(func=cmd_list)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

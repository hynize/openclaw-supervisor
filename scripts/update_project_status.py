#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
STATUS_PATH = PROJECT_ROOT / 'runtime' / 'project_status.json'


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_status():
    if STATUS_PATH.exists():
        return json.loads(STATUS_PATH.read_text(encoding='utf-8'))
    return {
        'current_focus': '',
        'current_milestone_deadline': '',
        'latest_artifacts': [],
        'completed_items': [],
        'incomplete_items': [],
        'last_updated': now_iso(),
    }


def save_status(data):
    data['last_updated'] = now_iso()
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def dedup_keep_latest(items):
    out = []
    seen = set()
    for item in reversed(items):
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return list(reversed(out))


def ensure_file(path_str):
    p = Path(path_str)
    if not p.exists():
        print(f'Error: Asset mismatch. File not found: {path_str}', file=sys.stderr)
        sys.exit(1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--set-focus')
    ap.add_argument('--set-deadline')
    ap.add_argument('--add-completed', action='append')
    ap.add_argument('--add-incomplete', action='append')
    ap.add_argument('--remove-incomplete', action='append')
    ap.add_argument('--add-artifact', action='append')
    ap.add_argument('--assert-file', action='append')
    ap.add_argument('--clear-completed', action='store_true')
    ap.add_argument('--clear-incomplete', action='store_true')
    args = ap.parse_args()

    data = load_status()

    for fp in (args.assert_file or []):
        ensure_file(fp)

    if args.set_focus is not None:
        data['current_focus'] = args.set_focus
    if args.set_deadline is not None:
        data['current_milestone_deadline'] = args.set_deadline
    if args.clear_completed:
        data['completed_items'] = []
    if args.clear_incomplete:
        data['incomplete_items'] = []
    if args.add_completed:
        data['completed_items'].extend(args.add_completed)
        data['completed_items'] = dedup_keep_latest(data['completed_items'])
    if args.add_incomplete:
        data['incomplete_items'].extend(args.add_incomplete)
        data['incomplete_items'] = dedup_keep_latest(data['incomplete_items'])
    if args.remove_incomplete:
        data['incomplete_items'] = [x for x in data['incomplete_items'] if x not in set(args.remove_incomplete)]
    if args.add_artifact:
        for art in args.add_artifact:
            data['latest_artifacts'].append(art)
        data['latest_artifacts'] = dedup_keep_latest(data['latest_artifacts'])[-5:]

    save_status(data)
    print(json.dumps(data, ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()

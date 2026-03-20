#!/usr/bin/env python3
"""
OpenClaw Supervisor - 一个通用且具备自律特性的任务执行监控与督促中间件。

功能:
1. 通过 start 启动监听任务，自动进行计时和目标跟踪。
2. 通过 check 单次检测当前任务的实际产生状态。
3. 通过 watch 模式作为常驻守护进程，执行【督促检查】和【全局汇报】双重节奏。
"""
import argparse
import json
import os
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# 取消个人的硬编码信息，引入全通用环境变量与标准化工作空间
DEFAULT_WORKSPACE = Path(os.path.expanduser('~')) / '.openclaw_supervisor' / 'runtime'
RUNTIME_DIR = Path(os.environ.get('OPENCLAW_SUPERVISOR_HOME', DEFAULT_WORKSPACE))
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)


def now_utc():
    return datetime.now(timezone.utc)

def iso(dt):
    return dt.astimezone(timezone.utc).isoformat()

def parse_iso(s):
    return datetime.fromisoformat(s)

def format_time(dt):
    """将 UTC 时间转化为可读本地时间格式字符串输出"""
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")

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

def load_task(task_id: str) -> dict:
    p = task_path(task_id)
    if not p.exists():
        raise FileNotFoundError(f'Task not found: {task_id}')
    return json.loads(p.read_text(encoding='utf-8'))

def save_task(task: dict):
    task_path(task['task_id']).write_text(json.dumps(task, ensure_ascii=False, indent=2), encoding='utf-8')

def append_history(event: dict):
    with history_path().open('a', encoding='utf-8') as f:
        f.write(json.dumps(event, ensure_ascii=False) + '\n')

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
        if exists and (mtime_ok or size_ok):
            any_artifact = True
        if not ok:
            all_ok = False
            
        checks.append({
            'path': fp, 
            'exists': exists, 
            'mtime_ok': mtime_ok, 
            'size_ok': size_ok, 
            'size': size, 
            'ok': ok
        })
    return checks, any_artifact, all_ok


# --- CORE COMMANDS ---

def cmd_start(args):
    if not args.expect_file:
        raise ValueError('必须提供至少一个 --expect-file 目标文件路径')
        
    created = now_utc()
    deadline = created + timedelta(minutes=args.deadline_min)
    expected_files = [str(Path(fp).resolve()) for fp in args.expect_file]
    
    task = asdict(TaskSpec(
        task_id=args.task_id,
        created_at=iso(created),
        deadline_at=iso(deadline),
        expected_files=expected_files,
        results={}
    ))
    save_task(task)
    append_history({'event': 'START', 'task_id': args.task_id, 'created_at': task['created_at'], 'deadline_at': task['deadline_at']})
    
    print(f"✅ 任务[{args.task_id}]启动成功！存档位置: {task_path(args.task_id)}")
    print(json.dumps(task, ensure_ascii=False, indent=2))


def process_check(task_id: str) -> dict:
    """核心判定逻辑隔离"""
    task = load_task(task_id)
    if task.get('status') in ['SUCCESS', 'TIMEOUT_NO_ARTIFACT', 'TIMEOUT_PARTIAL']:
        return task
        
    checks, any_artifact, all_ok = inspect_files(task)
    deadline = parse_iso(task['deadline_at'])
    now = now_utc()
    
    if all_ok and task['expected_files']:
        status = 'SUCCESS'
    elif now >= deadline and not any_artifact:
        status = 'TIMEOUT_NO_ARTIFACT'
    elif now >= deadline and any_artifact:
        status = 'TIMEOUT_PARTIAL'
    else:
        status = 'PENDING'
        
    task['status'] = status
    task['results'] = {'files': checks, 'checked_at': iso(now)}
    save_task(task)
    append_history({'event': 'CHECK', 'task_id': task_id, 'status': status, 'checked_at': iso(now)})
    return task


def cmd_check(args):
    task = process_check(args.task_id)
    print(json.dumps(task, ensure_ascii=False, indent=2))


def cmd_list(args):
    items = []
    for p in sorted(RUNTIME_DIR.glob('*.json')):
        if p.name == 'history.jsonl':
            continue
        try:
            items.append(json.loads(p.read_text(encoding='utf-8')))
        except Exception:
            pass
    print(json.dumps(items, ensure_ascii=False, indent=2))


def cmd_watch(args):
    """
    智能看门狗模式 (Daemon)。
    包含了自动督促节奏（Urge Rhythm）与总结汇报节奏（Report Rhythm）。
    """
    check_rhythm = args.check_interval
    report_rhythm = args.report_interval
    
    print(f"🚀 OpenClaw Supervisor 进入巡航守护模式 ...")
    print(f"📊 [全局督促节奏]: 每 {check_rhythm} 秒检查一遍存活任务卡死与超时情况")
    print(f"📈 [全局汇报节奏]: 每 {report_rhythm} 秒打印一次总体盘点报告")
    print("-" * 60)
    
    last_report_time = time.time()
    
    while True:
        try:
            now_ts = time.time()
            current_dt = now_utc()
            
            # 1. 督促环节 (Urge) - 获取当前全部任务并单独过一次状态
            pending_tasks = []
            for p in RUNTIME_DIR.glob('*.json'):
                if p.name == 'history.jsonl': continue
                data = json.loads(p.read_text(encoding='utf-8'))
                if data.get('status') == 'PENDING':
                    # 更新状态侦测
                    updated = process_check(data['task_id'])
                    
                    if updated['status'] == 'SUCCESS':
                        print(f"[{format_time(current_dt)}] 🎉 捷报！任务 [{updated['task_id']}] 目标文件已安全生成并核验通过！")
                    elif updated['status'].startswith('TIMEOUT'):
                        print(f"[{format_time(current_dt)}] 🚨 警报！任务 [{updated['task_id']}] 执行超时，状态判定为: {updated['status']}")
                    else:
                        # 仍是 PENDING，计算余量提醒
                        deadline = parse_iso(updated['deadline_at'])
                        rem_seconds = (deadline - current_dt).total_seconds()
                        if rem_seconds < 60 and rem_seconds > 0:
                            print(f"[{format_time(current_dt)}] ⏱️ 紧急督促：任务 [{updated['task_id']}] 距离死线仅剩 {int(rem_seconds)} 秒，请加快执行进度！")
                        elif rem_seconds > 0:
                            pending_tasks.append(updated['task_id'])
                            
            # 2. 汇报环节 (Report)
            if now_ts - last_report_time >= report_rhythm:
                all_status = {'SUCCESS': 0, 'PENDING': 0, 'TIMEOUT_NO_ARTIFACT': 0, 'TIMEOUT_PARTIAL': 0}
                for p in RUNTIME_DIR.glob('*.json'):
                    if p.name == 'history.jsonl': continue
                    data = json.loads(p.read_text(encoding='utf-8'))
                    s = data.get('status', 'PENDING')
                    if s in all_status:
                        all_status[s] += 1
                        
                print("\n" + "="*50)
                print(f"📋 【OpenClaw 阶段性状态盘点汇报】 | {format_time(current_dt)}")
                print(f" > 正在持续等待的健康任务数 : {all_status['PENDING']}")
                print(f" > 历史圆满完成的任务数     : {all_status['SUCCESS']}")
                print(f" > 超时失败并缺失产物任务数 : {all_status['TIMEOUT_NO_ARTIFACT']}")
                print(f" > 超时失败但存在中间产物数 : {all_status['TIMEOUT_PARTIAL']}")
                print("="*50 + "\n")
                
                last_report_time = now_ts
                
        except Exception as e:
            print(f"[{format_time(now_utc())}] ⚠️ 监控器遇到干扰异常: {e}")
            
        time.sleep(check_rhythm)


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Task Supervisor (任务泛用巡航督导引擎)")
    sub = parser.add_subparsers(dest='cmd', required=True)

    # 启动命令
    p_start = sub.add_parser('start', help="新建并启动一个目标文件的计时侦测任务")
    p_start.add_argument('--task-id', required=True, help="自定义的唯一任务编号或标识")
    p_start.add_argument('--deadline-min', type=int, required=True, help="任务的预期交付时长(分钟)，用于计算超时")
    p_start.add_argument('--expect-file', action='append', help="预期的产物文件路径(支持多个)")
    p_start.set_defaults(func=cmd_start)

    # 检查命令
    p_check = sub.add_parser('check', help="单次手动核验指定的某项任务结果")
    p_check.add_argument('--task-id', required=True, help="需要提取查验的任务标识")
    p_check.set_defaults(func=cmd_check)

    # 列表命令
    p_list = sub.add_parser('list', help="全览打印目前库中登记的所有任务结果数据源")
    p_list.set_defaults(func=cmd_list)
    
    # 守护进程命令
    p_watch = sub.add_parser('watch', help="开启监控探头模式，在后台依照频率全自动催办汇报")
    p_watch.add_argument('--check-interval', type=int, default=10, help="全盘侦测状态检查的步长/秒 (默认 10)")
    p_watch.add_argument('--report-interval', type=int, default=300, help="输出整体盘点状态看板的周期/秒 (默认 300)")
    p_watch.set_defaults(func=cmd_watch)

    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()

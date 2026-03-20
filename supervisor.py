#!/usr/bin/env python3
"""
OpenClaw Supervisor (Ultimate Firepower Edition) 
- 任务执行监控、资源探头与防线崩溃自起守护。

功能:
1. 通过 start 启动监听任务，可捕获 PID，甚至可配置崩溃自动被守护进程秒级拉起。
2. 通过 check 单次检测当前任务实体生成情况。
3. 通过 watch 作为常驻守护进程，执行检查督促、崩溃感知、自动重启、性能监控 (CPU/内存) 指标播报。
"""
import argparse
import json
import os
import time
import subprocess
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
    return dt.astimezone().strftime("%Y-%m-%d %H:%M:%S")

@dataclass
class TaskSpec:
    task_id: str
    created_at: str
    deadline_at: str
    expected_files: list
    pid: int = None
    command: str = None
    auto_restart: bool = False
    restarts_count: int = 0
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
            
        checks.append({'path': fp, 'exists': exists, 'mtime_ok': mtime_ok, 'size_ok': size_ok, 'size': size, 'ok': ok})
    return checks, any_artifact, all_ok


def check_process_status(pid: int):
    """
    检查进程是否存活并获取资源占用。
    返回值: (is_alive, cpu_percent, memory_mb)
    """
    if pid is None:
        return False, 0.0, 0.0
    try:
        # 兼容 Linux
        res = subprocess.check_output(['ps', '-p', str(pid), '-o', '%cpu,rss', '--no-headers'], stderr=subprocess.DEVNULL)
        parts = res.decode('utf-8').strip().split()
        if len(parts) >= 2:
            cpu = float(parts[0])
            mem_mb = float(parts[1]) / 1024.0 # KB to MB
            return True, cpu, mem_mb
    except Exception:
        # Windows fallback or process vanished
        pass
        
    # 纯检测心跳
    try:
        os.kill(pid, 0)
        return True, 0.0, 0.0
    except OSError:
        return False, 0.0, 0.0


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
        pid=args.pid,
        command=args.command,
        auto_restart=args.auto_restart,
        results={}
    ))
    save_task(task)
    append_history({'event': 'START', 'task_id': args.task_id, 'created_at': task['created_at'], 'deadline_at': task['deadline_at'], 'pid': args.pid})
    
    print(f"✅ 任务[{args.task_id}]启动成功！存档位置: {task_path(args.task_id)}")
    
    if args.auto_restart and not args.command:
        print("⚠️ 警告: 开启了自动拉起(--auto-restart) 但并未提供基础拉起命令(--command)，当进程崩溃时将无法自动重启该 Agent！")


def process_check(task_id: str) -> dict:
    task = load_task(task_id)
    if task.get('status') in ['SUCCESS', 'TIMEOUT_NO_ARTIFACT', 'TIMEOUT_PARTIAL', 'CRASHED_FAILED']:
        return task
        
    checks, any_artifact, all_ok = inspect_files(task)
    deadline = parse_iso(task['deadline_at'])
    now = now_utc()
    
    status = 'PENDING'
    if all_ok and task['expected_files']:
        status = 'SUCCESS'
    elif now >= deadline and not any_artifact:
        status = 'TIMEOUT_NO_ARTIFACT'
    elif now >= deadline and any_artifact:
        status = 'TIMEOUT_PARTIAL'
        
    task['status'] = status
    task['results'] = {'files': checks, 'checked_at': iso(now)}
    save_task(task)
    if status != 'PENDING':
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


def handle_process_crash_and_resources(task: dict, current_dt):
    pid = task.get('pid')
    cmd = task.get('command')
    auto = task.get('auto_restart')
    
    if pid is None:
        return task
        
    is_alive, cpu_pct, mem_mb = check_process_status(pid)
    
    if is_alive:
        # 有效性能报告
        if cpu_pct > 0 or mem_mb > 0:
            print(f"[{format_time(current_dt)}] 💻 性能探针：任务 [{task['task_id']}] 运行稳健 | 占用 CPU: {cpu_pct}% | 消耗内存: {mem_mb:.1f} MB")
        return task

    # 程序死亡 (崩溃或被杀)
    print(f"[{format_time(current_dt)}] 🔥 险情！守护引擎侦测到任务 [{task['task_id']}] 的 Agent 进程 (PID: {pid}) 已经异常终止退出！")
    
    if auto and cmd:
        print(f"[{format_time(current_dt)}] 🔄 [防线启动] 秒级拉起特性激活！正在尝试将指挥流重新注入，重启 Agent ...")
        # 直接静默拉起，通过 shell
        try:
            # Popen 触发无需等待挂起
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            task['pid'] = proc.pid
            task['restarts_count'] = task.get('restarts_count', 0) + 1
            print(f"[{format_time(current_dt)}] ✅ 成功复活！新接管进程 PID: {proc.pid} 载入追踪系统。")
            save_task(task)
            append_history({'event': 'RESTART', 'task_id': task['task_id'], 'new_pid': proc.pid})
        except Exception as e:
            print(f"[{format_time(current_dt)}] ❌ 拉起失败: {e}")
            task['status'] = 'CRASHED_FAILED'
            save_task(task)
    else:
        print(f"[{format_time(current_dt)}] 💔 该任务未开启 --auto-restart 或缺少 --command 字段，将丧失自动重启机会。已记录宕机状态。")
        task['status'] = 'CRASHED_FAILED'
        save_task(task)

    return task


def cmd_watch(args):
    check_rhythm = args.check_interval
    report_rhythm = args.report_interval
    
    print(f"🚀 OpenClaw Supervisor (Firepower Edition) 进入巡航守护模式 ...")
    print(f"📊 [全局探测引擎]: 每 {check_rhythm} 秒检查进程异常崩溃、资源波峰并执行起死回生拉起")
    print(f"📈 [极客看板汇报]: 每 {report_rhythm} 秒汇总打印一次高视角统筹报表")
    print("-" * 60)
    
    last_report_time = time.time()
    
    while True:
        try:
            now_ts = time.time()
            current_dt = now_utc()
            
            pending_count = 0
            
            # 1. 督促与性能探针环节 (Urge & Resurrect)
            for p in RUNTIME_DIR.glob('*.json'):
                if p.name == 'history.jsonl': continue
                data = json.loads(p.read_text(encoding='utf-8'))
                if data.get('status') == 'PENDING':
                    # 更新状态探测
                    updated = process_check(data['task_id'])
                    
                    if updated['status'] == 'SUCCESS':
                        print(f"[{format_time(current_dt)}] 🎉 捷报！特工任务 [{updated['task_id']}] 目标文件已安全生成并核验通过！")
                        continue
                    elif updated['status'].startswith('TIMEOUT') or updated['status'] == 'CRASHED_FAILED':
                        print(f"[{format_time(current_dt)}] 🚨 警报高悬！任务 [{updated['task_id']}] 执行宣告失败，终局判定为: {updated['status']}")
                        continue
                        
                    # 余量警报
                    deadline = parse_iso(updated['deadline_at'])
                    rem_seconds = (deadline - current_dt).total_seconds()
                    if rem_seconds < 60 and rem_seconds > 0:
                        print(f"[{format_time(current_dt)}] ⏱️ 连环督促：任务 [{updated['task_id']}] 距离死线仅剩 {int(rem_seconds)} 秒，请加快计算调度！")
                        
                    # 崩溃感知拉起与CPU/Memory探测
                    updated = handle_process_crash_and_resources(updated, current_dt)
                    if updated['status'] == 'PENDING':
                        pending_count += 1
                        
            # 2. 汇报环节 (Report)
            if now_ts - last_report_time >= report_rhythm:
                all_status = {'SUCCESS': 0, 'PENDING': 0, 'TIMEOUT_NO_ARTIFACT': 0, 'TIMEOUT_PARTIAL': 0, 'CRASHED_FAILED': 0}
                total_restarts = 0
                for p in RUNTIME_DIR.glob('*.json'):
                    if p.name == 'history.jsonl': continue
                    data = json.loads(p.read_text(encoding='utf-8'))
                    s = data.get('status', 'PENDING')
                    if s in all_status:
                        all_status[s] += 1
                    total_restarts += data.get('restarts_count', 0)
                        
                print("\n" + "="*50)
                print(f"📋 【OpenClaw 阶段性状态防线盘点】 | {format_time(current_dt)}")
                print(f" > 正在持续等待的健康存活任务 : {all_status['PENDING']}")
                print(f" > 历史圆满完成的胜利闭环     : {all_status['SUCCESS']}")
                print(f" > 超时失败并缺失产物任务数   : {all_status['TIMEOUT_NO_ARTIFACT']}")
                print(f" > 在执行中途遭遇无法挽回宕机 : {all_status['CRASHED_FAILED']}")
                print(f"✨ 守护引擎共计执行秒级拉起操作 : {total_restarts} 人次挽救执行期")
                print("="*50 + "\n")
                
                last_report_time = now_ts
                
        except Exception as e:
            print(f"[{format_time(now_utc())}] ⚠️ 监控器遇到干扰异常: {e}")
            
        time.sleep(check_rhythm)


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Task Supervisor - Ultimate Firepower Edition")
    sub = parser.add_subparsers(dest='cmd', required=True)

    p_start = sub.add_parser('start', help="新建并启动一个目标文件的计时侦测任务")
    p_start.add_argument('--task-id', required=True, help="自定义的唯一任务编号或标识")
    p_start.add_argument('--deadline-min', type=int, required=True, help="预期交付时长(分钟)")
    p_start.add_argument('--expect-file', action='append', help="预期的产物文件路径(支持多个)")
    p_start.add_argument('--pid', type=int, help="Agent挂钩绑定的真实进程PID标识 (从而开启 CPU/RAM探针和崩溃保护)", default=None)
    p_start.add_argument('--command', type=str, help="该节点由于各种原因挂掉时候，重新拉起它的启动脚本与参数", default=None)
    p_start.add_argument('--auto-restart', action='store_true', help="开启秒级重生开关。当配合 --pid 与 --command 时，进程一旦终止即可光速接管复活")
    p_start.set_defaults(func=cmd_start)

    p_check = sub.add_parser('check', help="单次手动核验")
    p_check.add_argument('--task-id', required=True)
    p_check.set_defaults(func=cmd_check)

    p_list = sub.add_parser('list')
    p_list.set_defaults(func=cmd_list)
    
    p_watch = sub.add_parser('watch', help="开启防线全备监控引擎在后台执行")
    p_watch.add_argument('--check-interval', type=int, default=10, help="全盘侦测步长/秒 (默认 10)")
    p_watch.add_argument('--report-interval', type=int, default=120, help="输出阶段报告周期/秒 (默认 120)")
    p_watch.set_defaults(func=cmd_watch)

    args = parser.parse_args()
    args.func(args)

if __name__ == '__main__':
    main()

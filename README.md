# OpenClaw Supervisor

针对长时间运行的 AI Agent 和自动化任务设计的可靠监控与状态自动化汇报组件。

## 核心功能

- **进程监控与自动重启**：监控指定进程 PID，在崩溃或非预期退出时自动重启。
- **资源监控**：实时查看被监控进程的 CPU 和内存占用情况。
- **自动化状态汇报**：同步项目进度，并在到达死线（Deadline）时自动生成汇总报告。
- **离线发信队列 (Outbox) 与重试机制**：通过异步队列确保消息可靠送达，支持失败重试。
- **告警聚合**：自动合并多条告警通知，防止消息轰炸。

---

## 🏗️ 系统架构

系统由两个核心层组成：
1. **核心监控层 (`supervisor.py`)**：负责进程级监控、资源统计及生命周期管理。
2. **心跳与汇报层 (`scripts/`)**：负责任务级死线追踪、产物核验及状态同步。

---

## 🛠️ 安装说明

```bash
git clone https://github.com/hynize/openclaw-supervisor.git
cd openclaw-supervisor
```
仅使用 Python 标准库，无需安装外部依赖即可满足核心功能。

---

## 🚀 快速上手

### 1. 进程保护
监控并自动重启任务：
```bash
python supervisor.py start \
  --task-id "demo-task-01" \
  --deadline-min 60 \
  --pid 1234 \
  --command "python agent.py" \
  --auto-restart
```

### 2. 任务死线与自动汇报
注册一个需要在规定时间内产出目标文件的任务：
```bash
# 1. 注册心跳任务
python scripts/execution_heartbeat.py start \
  --task-id "sync-task" \
  --deadline-min 30 \
  --expect-file "output/report.md"

# 2. 更新项目实时状态（用于自动汇报内容展示）
python scripts/update_project_status.py \
  --set-focus "feature-development" \
  --add-incomplete "task-alpha"
```

### 3. 开启后台消费线程
启动异步消息消费者以处理发信队列：
```bash
nohup bash scripts/message_consumer.sh &
```

---

## 📂 组件清单

- `scripts/execution_heartbeat.py`: 状态机核心，负责死线追踪与产物回收。
- `scripts/execution_heartbeat_dispatcher.py`: 告警聚合器。
- `scripts/execution_heartbeat_sender.py`: 异步发信器，支持失败重试逻辑。
- `scripts/update_project_status.py`: 项目状态同步接口。
- `runtime/project_status.example.json`: 项目状态追踪模板。

## 适用场景
适用于需要长时间运行自动化脚本、网页爬虫或 AI 驱动的 Agent，且需要高可用性和结构化进度反馈的开发者。

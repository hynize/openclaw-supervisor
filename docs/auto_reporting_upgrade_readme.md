# 自动汇报项目归档（2026-03-20）

## 项目目标
将“X 分钟后汇报”从口头承诺，升级为可观测、可审计、可自动触发的工程闭环，使系统能够在超时后自动主动发送项目状态汇报，而不是只发固定提醒。

## 已实现的目标
1. 执行监督器 heartbeat：支持 start/check/watch/alarm/notify
2. Dispatcher：将 notify 转化为待发送消息
3. Sender：消费 outbox，并通过 `openclaw message send` 实际发出消息
4. 状态快照：`runtime/project_status.json`
5. 状态汇报生成器：`scripts/status_report_generator.py`
6. 已完成 1 分钟自动状态汇报闭环验证

## 实现方式
### 1. Heartbeat 层
- `scripts/execution_heartbeat.py`
- 支持：
  - `start`
  - `check`
  - `watch`
  - `alarm`
  - `notify`

### 2. Dispatcher / Outbox 层
- `scripts/execution_heartbeat_dispatcher.py`
- 目录结构：
  - `runtime/execution_heartbeat/outbox/ready_to_send/`
  - `runtime/execution_heartbeat/outbox/processing/`
  - `runtime/execution_heartbeat/outbox/sent/`
  - `runtime/execution_heartbeat/outbox/failed/`

### 3. Sender 层
- `scripts/execution_heartbeat_sender.py`
- 通过 `openclaw message send` 调用统一消息发送能力

### 4. 状态汇报层
- `runtime/project_status.json`
- `scripts/update_project_status.py`
- `scripts/status_report_generator.py`

### 5. 自动消费层
- `scripts/message_consumer.sh`
- 每 10 秒轮询 dispatcher + sender

## 关键代码文件
- `scripts/execution_heartbeat.py`
- `scripts/execution_heartbeat_dispatcher.py`
- `scripts/execution_heartbeat_sender.py`
- `scripts/status_report_generator.py`
- `scripts/update_project_status.py`
- `scripts/message_consumer.sh`
- `runtime/project_status.json`
- `skills/artifact-driven-execution/SKILL.md`

## 关键经验总结
1. 无产物不算推进
2. 定时承诺必须转成真实机制
3. `watch -> alarm -> notify` 不等于完成
4. 必须有单一真理源：`runtime/project_status.json`
5. 自动汇报必须发“状态”，不是只发“提醒”
6. 自动汇报完成定义：用户真实收到自动状态消息

## 当前状态
- 自动主动汇报闭环：已打通
- 已验证：1 分钟自动状态汇报测试通过
- 已固化到 skill / docs / runtime

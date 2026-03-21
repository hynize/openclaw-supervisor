# 2026-03-20 自动主动汇报闭环 Review

## 目标
把“X分钟后汇报”从口头承诺，升级成真正的工程闭环。

## 已完成闭环
当前已跑通：

```text
execution_heartbeat start/check/watch
→ timeout
→ alarm.json
→ notify.json
→ dispatcher
→ outbox/ready_to_send
→ sender
→ openclaw message send
→ 用户收到项目状态自动汇报
```

## 当前关键组件
- `scripts/execution_heartbeat.py`
- `scripts/execution_heartbeat_dispatcher.py`
- `scripts/execution_heartbeat_sender.py`
- `scripts/status_report_generator.py`
- `scripts/update_project_status.py`
- `runtime/project_status.json`
- `scripts/message_consumer.sh`

## 本次最终打通点
1. Heartbeat 超时检测已稳定
2. `notify` 可生成
3. Dispatcher 已改为生成状态汇报消息（非固定提醒）
4. Sender 已统一切到 `ready_to_send -> processing -> sent/failed`
5. CLI bridge (`openclaw message send`) 已验证可用
6. 1分钟状态汇报测试已打通，用户可收到真正的项目状态汇报

## 关键教训
### 1. 无产物不算推进
没有新文件/结果/状态变化，就不能汇报“推进了”。

### 2. 定时承诺必须转成真实机制
“30分钟后汇报”不能只口头答应，必须注册 heartbeat/watch 或其他外部监督器。

### 3. 监督器本身不够，必须闭环到主动消息发送
`watch -> alarm -> notify` 不等于自动汇报完成；只有消息真正发到用户手里，才算完成。

### 4. 状态汇报必须有单一真理源
不能临时解析一堆 markdown/docs 现算，必须维护：
- `runtime/project_status.json`
并通过：
- `scripts/update_project_status.py`
统一更新。

### 5. 自动汇报消息必须发“状态”而不是“提醒”
最终用户要的是：
- 当前焦点
- 已补齐项
- 未补齐项
- 最新产物
而不是一句“请立即汇报当前进度”。

## 当前状态
- 自动主动汇报闭环：已打通
- 可作为默认外部监督机制：是
- 后续可继续扩展：是

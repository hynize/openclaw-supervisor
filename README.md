# OpenClaw Supervisor (大波威力加强版)

🤖 全网唯一 **拒绝 AI 罢工** 与 **自证清白** 的神仙级外挂“包工头”组件！

## 为什么你的 OpenClaw 离不开它？

家人们！正在折腾 OpenClaw 或是各类自动 Agent 的极客兄弟姐妹们看过来！👋 
是不是总觉得后台跑着长时间 AI 脚本当甩手掌柜时心里很慌？
程序挂了还以为它在发呆？或者担心把服务器内存直接撑爆死机？

不用折磨自己了，装上 `openclaw-supervisor`，让你彻底体验闭眼放养执行流的快乐！✨

### 🔥 核心暴脾气能力
✅ **全天候“监工”与起死回生：**  
在最新版中，你可以在任务注册时向监工出示你 Agent 的进程凭证。它一旦在巡视中发现你的执行流不小心崩溃消失了，它会利用自带的 `Auto-Restart` 强制火力在死线之内一秒光速拉起、原地复活，绝不妥协！让你的 Agent 号称 24h 永不掉线！

✅ **透明可视化的体检控：**  
告别一切黑盒盲猜瞎翻 Error 日志的日子。只要将进程 PID 输入监工网络内，在全局动态节奏监控探测中，它会实时为你播报目标任务在内存中的占用空间容量以及真实的底层 CPU 算力！你 Agent 当前到底是不是老牛推破车，全看这透明图表！

✅ **[NEW] 深度自动状态汇报闭环：**
不仅仅是简单的告警！系统现在拥有完整的 `Outbox` 离线发信队列和“状态快照”能力。即使你不在现场，监工也会在死线到达时自动汇总当前的“已完成项”、“未完成项”及“最新产物”，主动通过 Telegram 发送到你手机上。

✅ **[NEW] 绝不动摇的自愈健壮性：**
新增后台 `check_all` 背景扫描、失败重试（Retry）补偿机制、以及报警聚合（Batching）能力。彻底告别孤儿任务和消息垃圾轰炸。

---

## 🏗️ 核心架构（2026-03-21 升级版）

项目现由两个核心模块并行协作：
1. **监控主程序 (`supervisor.py`)**：负责进程级别的监控、资源统计、自动重启。
2. **自动汇报流水线 (`scripts/`)**：负责业务级别的死线倒计时、产物检查、状态同步及 Outbox 异步发信。

---

## 🛠️ 安装

```bash
git clone https://github.com/hynize/openclaw-supervisor.git
cd openclaw-supervisor
```
无需 `pip install` 的纯内置标准库。

---

## 🚀 实弹演练教程

### 场景 1：进程保护（经典能力）
督促 `pid 6666` 并在崩溃时自动重启：
```bash
python supervisor.py start \
  --task-id "Super-Render-101" \
  --deadline-min 45 \
  --pid 6666 \
  --command "python agent.py" \
  --auto-restart
```

### 场景 2：业务死线与自动汇报（升级版能力）
注册一个需要在 30 分钟内产出 `result.md` 的任务，并开启状态监控：
```bash
# 1. 注册心跳任务
python scripts/execution_heartbeat.py start \
  --task-id "Daily-Report-Sync" \
  --deadline-min 30 \
  --expect-file "docs/result.md"

# 2. 更新项目实时状态（用于自动汇报内容展示）
python scripts/update_project_status.py \
  --set-focus "整改主链规范" \
  --add-incomplete "完成 A 模块"
```

### 场景 3：启动后台“总监外挂”（必选）
这会让系统进入完全自动化的“扫描 -> 派发 -> 重试”闭环：
```bash
nohup bash scripts/message_consumer.sh &
```

---

## 📂 升级版组件清单
- `scripts/execution_heartbeat.py`: 核心状态机，支持背景扫描、迟到产物回收。
- `scripts/execution_heartbeat_dispatcher.py`: 报警聚合器，合并多项通知，防骚扰。
- `scripts/execution_heartbeat_sender.py`: 异步发信器，支持 3 次失败重试。
- `scripts/update_project_status.py`: 唯一的项目状态同步接口。
- `runtime/project_status.json`: 系统单一真理源，存储所有汇报细节。

## 面向对象
如果你是：追求自动化任务不断连跑量闭环的高阶玩家、受够了脚本经常由于偶发 OOM 退出的极客开发者，这就是你补齐架构体验的最后一块完美拼图。

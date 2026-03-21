# 深入推演：进度督促与自动汇报环节的边缘极限测试 (2026-03-21)

针对“基于文件产物的心跳监督 + 自动状态汇报”这一闭环，我们放弃正常的“理想执行流”，转而站在**恶意模拟、极端异常和常态化遗漏**的角度进行深度推演。

以下推演暴露出当前机制的 **5个高阶盲区（Vulnerabilities）**：

---

## 漏洞1：Watcher（守望者）进程的生死盲区
**场景描述**：
AI 承诺“30分钟后汇报”，并调用了 `python execution_heartbeat.py watch --task-id task1 --interval-sec 30`。
但是，10分钟后，由于主机重启、Docker 容器 OOM（内存溢出）或者父进程异常终止，这个 `watch` 循环被强行杀死了。
**推演结果**：
此任务变成了永远的孤儿。虽然它的状态是 `PENDING`，由于没有任何人再去 `check` 它，30分钟的死线到来时，**超时报警不会被触发，notify.json 不会生成，最终用户根本收不到任何自动汇报。**
**结论**：依赖常驻前台的 `watch` 进程来进行“超时检测”是脆弱的。
**演进建议**：应在 `message_consumer.sh` (或系统的 Cron 守护进程) 中加入全局扫描：让消费者每隔一段时间不仅读 outbox，还要主动扫一遍所有 `PENDING` 状态的 `.json` 任务并调用一次 `check`。

## 漏洞2：状态报告的“刻舟求剑”（状态脱节）
**场景描述**：
AI 正在开发功能，`heartbeat` 设定的目标是产生文件 A。
AI 非常努力，在超时前 1 分钟生成了完美的文件 A。`watch` 进程检测到文件，将任务标记为 `SUCCESS` 并退出。
接着，老板或用户发起了状态质询，或者另一个任务刚好触发了超时报警。`status_report_generator.py` 启动，去读取 `project_status.json`。
**推演结果**：
因为 AI 只是生成了文件 A，**它忘记了**调用 `update_project_status.py --remove-incomplete A --add-completed A`！
因此，生成的自动汇报里，赫然显示着：“**⏳ 未补齐项：A**”。
用户看到报告，以为 AI 还在摸鱼，实际上任务已经完成了。
**结论**：`execution_heartbeat` 里的文件状态与 `project_status` 是割裂的。
**演进建议**：`heartbeat` 进入 `SUCCESS` 时，必须有钩子（hook）能自动将该任务从 `project_status.json` 的 `incomplete` 转移到 `completed`，或者至少在状态报告里将 `heartbeat` 的底层成功状态合并展现。

## 漏洞3：发送失败的“死亡墓地”（无重试机制）
**场景描述**：
任务确实超时了，生成了 `ready_to_send`。
Sender 脚本被唤醒，去调用 `openclaw message send` 发送 Telegram 消息。
但不巧，此时 Telegram 服务器闪断、或者本地网络出现 20 秒的网络波动（DNS 解析失败）。
**推演结果**：
`subprocess.run` 返回失败代码。Sender 根据逻辑：
```python
else: os.rename(processing, failed)
```
它把这条极其重要的超时告警消息扔进了 `failed/` 文件夹。然后……**就再也没有然后了**。
Sender 脚本没有任何逻辑会去扫 `failed/` 并进行指数退避重试（Exponential Backoff Retry）。消息被永久雪藏，用户依然在苦苦等待汇报。
**结论**：Outbox 模式只有“发件箱”，没有“重试队列”。
**演进建议**：修改 `execution_heartbeat_sender.py`，允许定期将 `failed/` 中重试次数未超过阈值的请求移回 `ready_to_send/`。

## 漏洞4：迟到的正义不被记录（无法从 Timeout 恢复）
**场景描述**：
AI 遇到了棘手的 Bug，死线到了，被判定为 `TIMEOUT_NO_ARTIFACT`，且向用户发出了“超时报警与状态汇报”。
用户回复：“知道了，继续修”。
10分钟后，AI 修好了 Bug，生成了目标文件。
**推演结果**：
任务在到达 `TIMEOUT_NO_ARTIFACT` 时，状态机就已经锁死了。后续无论这个文件诞生得多么完美，系统都认为它仍然是“Timeout”。
不会向用户补发一句：“🟢 [恢复正常] 之前的超时任务已补齐产物”。
**结论**：缺少 `LATE_SUCCESS` 的状态流转，系统缺少自动纠偏带来的成就感闭环。
**演进建议**：在 `evaluate` 函数中，对已超时的任务在后续 `check` 时如果检测到文件达标，将其升级为 `LATE_SUCCESS` 并单独触发一次成功的 Notify。

## 漏洞5：消息风暴（Message Spamming）
**场景描述**：
AI 并发开了 5 个子任务打底，时间全部设定为 12:00 结束。
12:00 一到，5 个任务集体超时。
**推演结果**：
Dispatcher 接到了 5 个 `notify.json`。它极为敬业地调用了 5 次 `status_report_generator.py`，生成了 5 封长达几十行的完整状态报告卡片，塞进 Outbox。
用户的手机会在 3 秒内心跳连环震动，收到 5 封几乎一模一样的长篇大论，区别仅在最底部挂着不同的 task_id。极有可能导致用户将此机器人屏蔽（Mute）。
**结论**：缺少报警合并（Debounce / Batching）机制。
**演进建议**：Dispatcher 发现多余 1 个 notify 时，应该合并它们，只生成一封包含“5个超时任务列表”的单一报告。

---

### 总结论
目前这套系统是一个**防君子不防意外**的初级工程 MVP：
- 它成功解决了“把口头承诺落地为代码约束”的从 0 到 1。
- 但在面临进程崩溃、网络波动、遗忘更新维护状态等“墨菲定律”场景时，它缺乏**自愈（Self-healing）能力**。

要达到商业级/成熟级的监督能力，最迫切的行动是补齐**失败重试（漏洞 3）** 和 **后台全局扫描（漏洞 1）**。

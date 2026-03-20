# OpenClaw Supervisor

`OpenClaw Supervisor` 是一个从原本生硬的检测探针剥离进化而成的**通用化、高度自律的任务执行泛用监控器与督导师**。它不仅可以被任何 Agent (如 OpenClaw)、第三方程序或者后台运算所调用产生进度追踪机制，还能够以特定的节奏为您进行状态的“催办督促”和“全局宏观报备”。

## 🌟 核心特性

1. **绝对脱敏与灵活泛用**：去除了所有针对单一部署机器的硬编码耦合。工作流会存放于标准化的家目录缓存 `~/.openclaw_supervisor/runtime`，也可通过 `OPENCLAW_SUPERVISOR_HOME` 环境变量跨盘重定向保护。
2. **生命周期原子记录**：所有的 `start` 和 `check` 都会产生精准到秒以及包含历史 `history.jsonl` 不可篡改动作的完整执行日志，提供完善的事后审计机制。
3. **多维健康评析体系**：从传统的一刀切改为引入 `TIMEOUT_NO_ARTIFACT` (极度失败停滞) 和 `TIMEOUT_PARTIAL` (超时但存在有效半成品) 等精细化状态标识。
4. **智能自动化督促与盘点循环 (`Watch` 模式)**：内置自巡航进程，拥有完全可被您自定义掌控的检测心跳 (`Check Rhythm`) 与阶段汇报 (`Report Rhythm`)，为管理大量并发长线程操作赋能。

---

## 🛠️ 安装与使用指南

将该项目 `git clone` 拉取到您的本地环境中。这是一个纯 Python3 驱动的高内聚脚本，除了原生的官方标准库之外，**绝对没有引入过任何外部多余或者需要 `pip` 安装的复杂依赖**。开箱直接运行即可！

### 1. 启动一个受监督的监控任务
假设我们需要让 OpenClaw 生成某张特定的效果图，且必须在 `45 分钟` 内完成。我们可以预先埋点：

```bash
python supervisor.py start --task-id "G-Design-101" --deadline-min 45 --expect-file "/app/outputs/final_render.png"
```
（你可以传入多个 `--expect-file`，将会必须满足全部被修改才判定为完美胜利。）

### 2. 即时人工抽检查询
查阅刚才创建的 `G-Design-101` 当前的状态变化：
```bash
python supervisor.py check --task-id "G-Design-101"
```
此命令将输出美观易懂的 JSON 元数据核验结果。

### 3. 打开智能管家后置视界 (推荐)
直接开启 `watch` 智能看门狗模式。它负责成为那个拿着秒表帮您全局统计的监工。

如果您觉得每 `300` 秒太慢了，您可以在启动时进行微调：
```bash
python supervisor.py watch --check-interval 15 --report-interval 60
```
- `--check-interval 15`: 代表它每 `15` 秒，就会将手头的全部 PENDING 任务刷一遍（**如果某个任务距离死线剩余不到1分钟，监工会自动高频拉响红色警报为您催办督促进程！**）。
- `--report-interval 60`: 代表每隔 `60` 秒整点，它就会梳理出一份全局表格，将总览当前所有未完成数、胜利数、超时数统统作为报告打印出来。

如果你希望能将其作为系统的服务常驻，可以使用 `nohup`：
```bash
nohup python supervisor.py watch > /var/log/openclaw_supervisor.log 2>&1 &
```

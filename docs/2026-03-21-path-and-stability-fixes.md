# 2026-03-21 代码修复与健壮性提升文档

## 目标
根据代码审查结果，对遗留的硬编码路径问题及可能导致静默挂掉的潜在致命错误进行修复和升级，提升项目在不同环境（本地测试、容器等）下的健壮性。

## 修改内容清单

### 1. 移除了全量 Python 脚本中的硬编码 Linux 绝对路径
之前的代码中所有的 `runtime/execution_heartbeat` 等目录都硬编码指到了内部固定的绝对路径下，导致离开容器无法本地执行。

**涉及文件**：
*   `execution_heartbeat.py`
*   `execution_heartbeat_dispatcher.py`
*   `execution_heartbeat_sender.py`
*   `update_project_status.py`

**修复方案**：
引入了统一的相对路径解析基底架构，通过获取执行脚本自身的绝对位置 (`__file__`)，反推出 `PROJECT_ROOT` 及相关的 `RUNTIME_DIR`、`STATUS_PATH` 等。
```python
# 修复示例用法：
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent
RUNTIME_DIR = PROJECT_ROOT / 'runtime' / 'execution_heartbeat'
```
这样不仅支持在 `/root/...` 下运行，在任何 Windows `C:\...` 或 Mac 环境下均能完全兼容。

### 2. 修复 `message_consumer.sh` 日志文件夹不存在引发的崩溃
原文件中的消费循环强制向 `workspace/logs/` 写入重定向日志：
```bash
python3 ... > /root/.../logs/message_consumer_dispatch.log
```
在 Bash 中，若 `logs` 目录不存在，该命令不仅无法记录，还会直接失败中止 `python` 命令的执行。

**涉及文件**：
*   `message_consumer.sh`

**修复方案**：
1. 同样使用了 Bash 内带的 `BASH_SOURCE[0]` 套路做相对环境锚定。
2. 显式添加了防御性创建目录的步骤：`mkdir -p "$PROJECT_ROOT/logs"`。
这样即便是新环境初次拉起，也绝不会因缺少文件夹而卡死主消费线程。

## 升级后效果
当前所有的心跳检测、派发处理、配置更新脚本都已经实现跨平台**零配置依赖**，你甚至可以在 Windows 本地直接 `python scripts/execution_heartbeat.py list` 来进行完整调度测试，再无任何由硬编码引发的错误。

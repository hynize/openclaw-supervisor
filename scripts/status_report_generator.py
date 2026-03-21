#!/usr/bin/env python3
import json
import os
import sys


def generate_report():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    json_path = os.path.join(project_root, "runtime", "project_status.json")

    if not os.path.exists(json_path):
        print(f"❌ 汇报失败：未找到状态文件 ({json_path})")
        sys.exit(1)

    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            status_data = json.load(f)
    except Exception as e:
        print(f"❌ 汇报失败：无法解析状态文件 - {e}")
        sys.exit(1)

    def format_list(items):
        if not items:
            return "- （暂无）"
        return "\n".join([f"- {item}" for item in items])

    focus = status_data.get("current_focus", "未指定")
    completed = status_data.get("completed_items", [])
    incomplete = status_data.get("incomplete_items", [])
    artifacts = status_data.get("latest_artifacts", [])
    last_updated = status_data.get("last_updated", "未知时间")

    report = f"""📊 [项目状态自动汇报]

🎯 焦点：{focus}

✅ 已补齐项：
{format_list(completed)}

⏳ 未补齐项：
{format_list(incomplete)}

📦 最新产物：
{format_list(artifacts)}

⏰ 快照时间：{last_updated}"""

    print(report)


if __name__ == "__main__":
    generate_report()

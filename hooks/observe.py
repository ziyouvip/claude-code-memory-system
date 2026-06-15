#!/usr/bin/env python3
"""
Observation采集脚本
在 Hook (PreToolUse/PostToolUse) 中调用，记录工具调用数据
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import uuid

# 配置路径
CLAUDE_DIR = Path.home() / ".claude"
OBSERVATIONS_DIR = CLAUDE_DIR / "observations"
OBSERVATIONS_FILE = OBSERVATIONS_DIR / "observations.jsonl"
SESSION_ID_FILE = CLAUDE_DIR / "observations" / ".session_id"


def get_or_create_session_id() -> str:
    """获取或创建当前会话ID"""
    if SESSION_ID_FILE.exists():
        return SESSION_ID_FILE.read_text().strip()
    session_id = str(uuid.uuid4())[:8]
    SESSION_ID_FILE.write_text(session_id)
    return session_id


def read_stdin() -> dict:
    """从stdin读取Hook传入的数据"""
    try:
        data = sys.stdin.read()
        if data:
            return json.loads(data)
    except json.JSONDecodeError:
        pass
    return {}


def record_observation(phase: str, tool_data: dict):
    """记录观测数据到JSONL文件"""
    # 确保目录存在
    OBSERVATIONS_DIR.mkdir(parents=True, exist_ok=True)

    # 构建观测记录
    observation = {
        "session_id": get_or_create_session_id(),
        "ts": datetime.now(timezone.utc).isoformat(),
        "phase": phase,
        "tool": tool_data.get("tool_name", "unknown"),
        "input": tool_data.get("tool_input", {}),
        "bash_desc": tool_data.get("bash_description"),
    }

    # 追加写入JSONL文件
    with open(OBSERVATIONS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(observation, ensure_ascii=False) + "\n")

    return observation


def main():
    if len(sys.argv) < 2:
        print("Usage: observe.py <pre|post>", file=sys.stderr)
        sys.exit(1)

    phase = sys.argv[1]
    if phase not in ("pre", "post"):
        print(f"Invalid phase: {phase}", file=sys.stderr)
        sys.exit(1)

    # 读取stdin中的工具调用数据
    tool_data = read_stdin()

    # 记录观测
    observation = record_observation(phase, tool_data)


if __name__ == "__main__":
    main()

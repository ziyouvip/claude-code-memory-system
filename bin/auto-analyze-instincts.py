#!/usr/bin/env python3
"""
Instinct 分析引擎
会话结束时运行，分析观测数据，提炼行为模式
"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# 配置路径
CLAUDE_DIR = Path.home() / ".claude"
OBSERVATIONS_FILE = CLAUDE_DIR / "observations" / "observations.jsonl"
INSTINCTS_DIR = CLAUDE_DIR / "homunculus" / "instincts" / "personal"

# 检测模式定义
PATTERNS = {
    "read-before-edit": {
        "trigger": "when about to edit a file that hasn't been read in this session",
        "action": "Use Read tool to read the file content before editing, especially when the file is long or has recent changes from others.",
        "domain": "workflow",
    },
    "test-after-change": {
        "trigger": "after making code changes to a project with tests",
        "action": "Run the test suite to verify changes don't break existing functionality.",
        "domain": "testing",
    },
    "git-status-check": {
        "trigger": "before starting significant work on a git-tracked project",
        "action": "Check git status to understand current state (branches, uncommitted changes).",
        "domain": "git",
    },
    "install-before-use": {
        "trigger": "before using a CLI tool that may not be installed",
        "action": "Check if the tool exists, and install it if needed.",
        "domain": "workflow",
    },
    "context-gather": {
        "trigger": "before making large-scale changes to a codebase",
        "action": "Gather context by reading key files, understanding architecture first.",
        "domain": "workflow",
    },
}


def load_observations() -> list[dict]:
    """加载观测数据"""
    if not OBSERVATIONS_FILE.exists():
        return []
    observations = []
    with open(OBSERVATIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    observations.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return observations


def detect_patterns(observations: list[dict]) -> dict[str, int]:
    """统计模式检测"""
    pattern_counts = defaultdict(int)

    # 按 session 分组
    sessions = defaultdict(list)
    for obs in observations:
        sessions[obs.get("session_id", "unknown")].append(obs)

    for session_id, session_obs in sessions.items():
        # 按时间排序
        session_obs.sort(key=lambda x: x.get("ts", ""))

        # 检测 read-before-edit
        read_files = set()
        for obs in session_obs:
            tool = obs.get("tool", "")
            if tool == "Read":
                file_path = obs.get("input", {}).get("file_path", "")
                if file_path:
                    read_files.add(file_path)
            elif tool == "Edit":
                file_path = obs.get("input", {}).get("file_path", "")
                if file_path and file_path in read_files:
                    pattern_counts["read-before-edit"] += 1

        # 检测 test-after-change
        has_edit = False
        for obs in session_obs:
            if obs.get("tool") in ("Edit", "Write"):
                has_edit = True
            elif has_edit and obs.get("tool") == "Bash":
                bash_input = obs.get("input", {}).get("command", "")
                if any(kw in bash_input for kw in ["test", "vitest", "jest", "pytest", "npm test"]):
                    pattern_counts["test-after-change"] += 1
                    break

        # 检测 git-status-check
        has_git_op = False
        for obs in session_obs:
            tool = obs.get("tool", "")
            if tool == "Bash":
                cmd = obs.get("input", {}).get("command", "")
                if "git status" in cmd or "git branch" in cmd:
                    has_git_op = True
                elif has_git_op and any(kw in cmd for kw in ["git commit", "git push", "git merge"]):
                    pattern_counts["git-status-check"] += 1

        # 检测 install-before-use
        for obs in session_obs:
            if obs.get("tool") == "Bash":
                cmd = obs.get("input", {}).get("command", "")
                if any(kw in cmd for kw in ["which ", "command -v", "--version", "npm install", "pip install"]):
                    pattern_counts["install-before-use"] += 1

        # 检测 context-gather
        read_count = sum(1 for obs in session_obs if obs.get("tool") == "Read")
        edit_count = sum(1 for obs in session_obs if obs.get("tool") in ("Edit", "Write"))
        if read_count >= 3 and edit_count > 0:
            pattern_counts["context-gather"] += 1

    return dict(pattern_counts)


def get_existing_instincts() -> dict[str, dict]:
    """加载现有Instinct"""
    instincts = {}
    if not INSTINCTS_DIR.exists():
        return instincts

    for file_path in INSTINCTS_DIR.glob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8")
            # 解析 frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = {}
                    for line in parts[1].strip().split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            frontmatter[key.strip()] = value.strip().strip('"')

                    instincts[frontmatter.get("id", file_path.stem)] = {
                        "path": file_path,
                        "frontmatter": frontmatter,
                        "content": parts[2].strip(),
                    }
        except Exception:
            continue

    return instincts


def create_instinct_file(pattern_id: str, pattern_data: dict, confidence: float):
    """创建Instinct文件"""
    INSTINCTS_DIR.mkdir(parents=True, exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    file_path = INSTINCTS_DIR / f"{pattern_id}.md"

    content = f"""---
id: {pattern_id}
trigger: "{pattern_data['trigger']}"
confidence: {confidence:.2f}
domain: {pattern_data['domain']}
source: session-observation
deprecated: false
observed_at: "{today}"
---

## Action
{pattern_data['action']}

## Evidence
Detected through statistical pattern analysis of tool usage observations.
"""

    file_path.write_text(content, encoding="utf-8")
    return file_path


def update_instinct_confidence(instinct: dict, delta: float):
    """更新Instinct置信度"""
    fm = instinct["frontmatter"]
    current = float(fm.get("confidence", 0.5))
    new_confidence = max(0.0, min(0.9, current + delta))

    fm["confidence"] = f"{new_confidence:.2f}"
    fm["deprecated"] = "false" if new_confidence >= 0.55 else "true"

    # 重建文件内容
    frontmatter_str = "\n".join(f"{k}: {v}" for k, v in fm.items())
    content = f"---\n{frontmatter_str}\n---\n\n{instinct['content']}"

    instinct["path"].write_text(content, encoding="utf-8")


def analyze_with_ai(observations: list[dict]) -> list[dict]:
    """AI语义分析（调用Claude CLI）"""
    # 采样最近的观测数据
    recent = observations[-50:] if len(observations) > 50 else observations

    # 构建摘要
    summary = []
    tool_counts = defaultdict(int)
    for obs in recent:
        tool_counts[obs.get("tool", "unknown")] += 1

    summary.append("Tool usage summary:")
    for tool, count in sorted(tool_counts.items(), key=lambda x: -x[1]):
        summary.append(f"  - {tool}: {count} times")

    # 提取 Bash 命令模式
    bash_commands = []
    for obs in recent:
        if obs.get("tool") == "Bash":
            cmd = obs.get("input", {}).get("command", "")[:100]
            if cmd:
                bash_commands.append(cmd)

    if bash_commands:
        summary.append("\nRecent Bash commands:")
        for cmd in bash_commands[-10:]:
            summary.append(f"  - {cmd}")

    prompt = f"""Analyze the following Claude Code usage patterns and suggest behavioral rules (instincts).

{chr(10).join(summary)}

Return a JSON array of instincts. Each instinct should have:
- id: kebab-case identifier
- trigger: when this rule should apply
- action: what action to take
- domain: category (workflow, testing, git, code-style, project-context)

Return ONLY the JSON array, no other text. Example:
[{{"id": "always-run-tests", "trigger": "after editing test files", "action": "run the test", "domain": "testing"}}]
"""

    try:
        result = subprocess.run(
            ["claude", "--print", "--model", "claude-haiku-4-5-20251001", "-p", prompt],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            output = result.stdout.strip()
            # 尝试解析JSON
            # 处理可能的 markdown 代码块
            if "```json" in output:
                output = output.split("```json")[1].split("```")[0]
            elif "```" in output:
                output = output.split("```")[1].split("```")[0]

            instincts = json.loads(output)
            return instincts
    except Exception as e:
        print(f"AI analysis failed: {e}", file=sys.stderr)

    return []


def main():
    # 加载观测数据
    observations = load_observations()
    if not observations:
        print("No observations to analyze")
        return

    print(f"Loaded {len(observations)} observations")

    # 加载现有 instincts
    existing = get_existing_instincts()

    # 路径 A: 统计模式检测
    pattern_counts = detect_patterns(observations)
    print(f"Detected patterns: {pattern_counts}")

    for pattern_id, count in pattern_counts.items():
        if pattern_id not in PATTERNS:
            continue

        pattern_data = PATTERNS[pattern_id]

        if pattern_id in existing:
            # 更新置信度
            update_instinct_confidence(existing[pattern_id], 0.05)
            print(f"Updated confidence for {pattern_id}")
        else:
            # 创建新 instinct
            confidence = min(0.9, 0.5 + count * 0.05)
            create_instinct_file(pattern_id, pattern_data, confidence)
            print(f"Created instinct: {pattern_id}")

    # 路径 B: AI 语义分析
    if len(observations) >= 20:  # 只有足够数据时才进行AI分析
        ai_instincts = analyze_with_ai(observations)
        for instinct in ai_instincts[:5]:  # 最多添加5条
            instinct_id = instinct.get("id", "")
            if instinct_id and instinct_id not in existing:
                create_instinct_file(
                    instinct_id,
                    {
                        "trigger": instinct.get("trigger", ""),
                        "action": instinct.get("action", ""),
                        "domain": instinct.get("domain", "workflow"),
                    },
                    0.5,
                )
                print(f"Created AI-derived instinct: {instinct_id}")

    print("Instinct analysis complete")


if __name__ == "__main__":
    main()

"""
Claude Code Memory System - Installer Module
"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

CLAUDE_DIR = Path.home() / ".claude"
REPO_URL = "https://raw.githubusercontent.com/yourname/claude-code-memory-system/main"

DIRS = [
    "hooks",
    "bin",
    "observations",
    "homunculus/instincts/personal",
    "memory/memories",
    "memory/qdrant",
    "rules",
]

FILES = {
    "hooks/observe.py": f"{REPO_URL}/hooks/observe.py",
    "bin/auto-analyze-instincts.py": f"{REPO_URL}/bin/auto-analyze-instincts.py",
    "bin/auto-evolve.py": f"{REPO_URL}/bin/auto-evolve.py",
    "bin/inject_memory_context.py": f"{REPO_URL}/bin/inject_memory_context.py",
    "bin/observations_rotate.py": f"{REPO_URL}/bin/observations_rotate.py",
}


def install(verbose: bool = True) -> bool:
    """
    Install Claude Code Memory System.

    Args:
        verbose: Print progress messages

    Returns:
        True if installation successful
    """
    if verbose:
        print("🚀 Installing Claude Code Memory System...")

    # Step 1: Create directories
    if verbose:
        print("  📁 Creating directories...")
    for dir_path in DIRS:
        full_path = CLAUDE_DIR / dir_path
        full_path.mkdir(parents=True, exist_ok=True)

    # Step 2: Download files
    if verbose:
        print("  📥 Downloading scripts...")
    import urllib.request

    for file_path, url in FILES.items():
        full_path = CLAUDE_DIR / file_path
        try:
            urllib.request.urlretrieve(url, full_path)
        except Exception as e:
            if verbose:
                print(f"    ⚠️  Failed to download {file_path}: {e}")
            # Try local copy if available
            local_file = Path(__file__).parent.parent.parent / file_path
            if local_file.exists():
                shutil.copy(local_file, full_path)

    # Step 3: Configure hooks
    if verbose:
        print("  ⚙️  Configuring hooks...")
    _configure_hooks()

    # Step 4: Create example memory
    if verbose:
        print("  📝 Creating example memory...")
    _create_example_memory()

    if verbose:
        print("\n✅ Installation complete!")
        print(f"   Installed to: {CLAUDE_DIR}")
        print("\n   Next steps:")
        print("   1. Restart Claude Code to activate")
        print("   2. Add custom memories to ~/.claude/memory/memories/")

    return True


def uninstall(verbose: bool = True) -> bool:
    """
    Uninstall Claude Code Memory System.

    Args:
        verbose: Print progress messages

    Returns:
        True if uninstallation successful
    """
    if verbose:
        print("🗑️  Uninstalling Claude Code Memory System...")

    # Remove hooks from settings.json
    settings_file = CLAUDE_DIR / "settings.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
            if "hooks" in settings:
                # Only remove our hooks
                our_hooks = ["PreToolUse", "PostToolUse", "Stop", "SessionStart"]
                for hook in our_hooks:
                    settings["hooks"].pop(hook, None)
                if not settings["hooks"]:
                    del settings["hooks"]
                settings_file.write_text(json.dumps(settings, indent=2))
                if verbose:
                    print("  ✓ Removed hooks configuration")
        except Exception as e:
            if verbose:
                print(f"  ⚠️  Failed to update settings.json: {e}")

    if verbose:
        print("\n✅ Uninstall complete!")
        print("   Note: Observation data and memories are preserved.")
        print(f"   Delete {CLAUDE_DIR}/observations and {CLAUDE_DIR}/memory to remove all data.")

    return True


def status(verbose: bool = True) -> dict:
    """
    Check installation status.

    Returns:
        Dict with status information
    """
    result = {
        "installed": False,
        "hooks_configured": False,
        "observation_count": 0,
        "instinct_count": 0,
        "memory_count": 0,
    }

    # Check if scripts exist
    observe_script = CLAUDE_DIR / "hooks" / "observe.py"
    if observe_script.exists():
        result["installed"] = True

    # Check hooks configuration
    settings_file = CLAUDE_DIR / "settings.json"
    if settings_file.exists():
        try:
            settings = json.loads(settings_file.read_text())
            if "hooks" in settings:
                result["hooks_configured"] = True
        except Exception:
            pass

    # Count observations
    obs_file = CLAUDE_DIR / "observations" / "observations.jsonl"
    if obs_file.exists():
        with open(obs_file) as f:
            result["observation_count"] = sum(1 for _ in f)

    # Count instincts
    instincts_dir = CLAUDE_DIR / "homunculus" / "instincts" / "personal"
    if instincts_dir.exists():
        result["instinct_count"] = len(list(instincts_dir.glob("*.md")))

    # Count memories
    memories_dir = CLAUDE_DIR / "memory" / "memories"
    if memories_dir.exists():
        result["memory_count"] = len(list(memories_dir.glob("*.md")))

    if verbose:
        print("📊 Claude Code Memory System Status")
        print("=" * 40)
        print(f"  Installed:         {'✅' if result['installed'] else '❌'}")
        print(f"  Hooks configured:  {'✅' if result['hooks_configured'] else '❌'}")
        print(f"  Observations:      {result['observation_count']}")
        print(f"  Instincts:         {result['instinct_count']}")
        print(f"  Memories:          {result['memory_count']}")

    return result


def _configure_hooks():
    """Configure hooks in settings.json"""
    settings_file = CLAUDE_DIR / "settings.json"

    if settings_file.exists():
        settings = json.loads(settings_file.read_text())
    else:
        settings = {}

    hooks_config = {
        "PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "python ~/.claude/hooks/observe.py pre"}]}
        ],
        "PostToolUse": [
            {"matcher": ".*", "hooks": [{"type": "command", "command": "python ~/.claude/hooks/observe.py post"}]}
        ],
        "Stop": [
            {"hooks": [{"type": "command", "command": "python ~/.claude/bin/auto-analyze-instincts.py && python ~/.claude/bin/auto-evolve.py"}]}
        ],
        "SessionStart": [
            {"hooks": [{"type": "command", "command": "python ~/.claude/bin/inject_memory_context.py"}]}
        ],
    }

    settings["hooks"] = hooks_config
    settings_file.write_text(json.dumps(settings, indent=2, ensure_ascii=False))


def _create_example_memory():
    """Create example memory file"""
    example_path = CLAUDE_DIR / "memory" / "memories" / "getting-started.md"

    if example_path.exists():
        return

    content = """---
name: getting-started
description: 快速入门指南
metadata:
  type: reference
---

## 系统已安装成功！

你已成功安装 Claude Code Memory System。

### 下一步
1. 重启 Claude Code 开始使用
2. 正常使用，系统会自动记录行为
3. 会话结束时自动分析模式
4. 下次会话自动加载学习到的规则

### 创建更多记忆
在 `~/.claude/memory/memories/` 目录下创建 `.md` 文件来添加记忆。

### 记忆类型
- `user`: 用户偏好、身份认知
- `feedback`: 纠正和指导
- `project`: 项目上下文
- `reference`: 外部资源引用
"""
    example_path.write_text(content)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "install":
            install()
        elif cmd == "uninstall":
            uninstall()
        elif cmd == "status":
            status()
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python -m claude_memory [install|uninstall|status]")
    else:
        install()

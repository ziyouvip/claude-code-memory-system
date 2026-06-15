#!/bin/bash
# Claude Code Memory System - 一键安装脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/ziyouvip/claude-code-memory-system/master/install.sh | bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

CLAUDE_DIR="$HOME/.claude"
REPO_URL="https://github.com/ziyouvip/claude-code-memory-system"

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Claude Code Memory System - Installer                 ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检查 Python
if ! command -v python3 &> /dev/null; then
    if ! command -v python &> /dev/null; then
        echo -e "${RED}Error: Python not found. Please install Python 3.8+${NC}"
        exit 1
    fi
    PYTHON="python"
else
    PYTHON="python3"
fi

echo -e "${YELLOW}Step 1/5${NC} Creating directories..."
mkdir -p "$CLAUDE_DIR/hooks"
mkdir -p "$CLAUDE_DIR/bin"
mkdir -p "$CLAUDE_DIR/observations"
mkdir -p "$CLAUDE_DIR/homunculus/instincts/personal"
mkdir -p "$CLAUDE_DIR/memory/memories"
mkdir -p "$CLAUDE_DIR/memory/qdrant"
mkdir -p "$CLAUDE_DIR/rules"

echo -e "${YELLOW}Step 2/5${NC} Downloading scripts..."
# 下载脚本
curl -fsSL "$REPO_URL/raw/master/hooks/observe.py" -o "$CLAUDE_DIR/hooks/observe.py"
curl -fsSL "$REPO_URL/raw/master/bin/auto-analyze-instincts.py" -o "$CLAUDE_DIR/bin/auto-analyze-instincts.py"
curl -fsSL "$REPO_URL/raw/master/bin/auto-evolve.py" -o "$CLAUDE_DIR/bin/auto-evolve.py"
curl -fsSL "$REPO_URL/raw/master/bin/inject_memory_context.py" -o "$CLAUDE_DIR/bin/inject_memory_context.py"
curl -fsSL "$REPO_URL/raw/master/bin/observations_rotate.py" -o "$CLAUDE_DIR/bin/observations_rotate.py"

echo -e "${YELLOW}Step 3/5${NC} Installing Python dependencies..."
$PYTHON -m pip install -q qdrant-client sentence-transformers 2>/dev/null || {
    echo -e "${YELLOW}Warning: pip install may need user confirmation${NC}"
    $PYTHON -m pip install qdrant-client sentence-transformers
}

echo -e "${YELLOW}Step 4/5${NC} Configuring hooks..."
# 检查 settings.json 是否存在
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
if [ -f "$SETTINGS_FILE" ]; then
    # 备份现有配置
    cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup.$(date +%Y%m%d%H%M%S)"
    echo -e "${GREEN}Backed up existing settings.json${NC}"
fi

# 下载配置合并脚本并执行
cat > /tmp/merge_settings.py << 'PYEOF'
import json
import sys
from pathlib import Path

settings_file = Path.home() / ".claude" / "settings.json"

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
    ]
}

if settings_file.exists():
    settings = json.loads(settings_file.read_text())
else:
    settings = {}

settings["hooks"] = hooks_config
settings_file.write_text(json.dumps(settings, indent=2, ensure_ascii=False))
print("Hooks configured successfully")
PYEOF

$PYTHON /tmp/merge_settings.py
rm /tmp/merge_settings.py

echo -e "${YELLOW}Step 5/5${NC} Creating example memory..."
EXAMPLE_MEMORY="$CLAUDE_DIR/memory/memories/getting-started.md"
cat > "$EXAMPLE_MEMORY" << 'EOF'
---
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
EOF

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║              Installation Complete!                       ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "Installed to: ${YELLOW}$CLAUDE_DIR${NC}"
echo ""
echo -e "Next steps:"
echo -e "  1. ${YELLOW}Restart Claude Code${NC} to activate the system"
echo -e "  2. Use Claude Code normally - your behavior will be learned"
echo -e "  3. Add custom memories to ${YELLOW}~/.claude/memory/memories/${NC}"
echo ""

#!/bin/bash
# Claude Code Memory System - 一键安装脚本
# 用法: curl -fsSL https://raw.githubusercontent.com/ziyouvip/claude-code-memory-system/master/install.sh | bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REPO_URL="https://raw.githubusercontent.com/ziyouvip/claude-code-memory-system/master"

# 默认安装 Claude Code
TOOL="${TOOL:-claude-code}"

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     Claude Code Memory System - Installer                 ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# 检测工具
detect_tool() {
    if [ -n "$TOOL" ]; then
        return
    fi

    if [ -d "$HOME/.claude" ]; then
        TOOL="claude-code"
    elif [ -d "$HOME/.opencode" ] || [ -d "$HOME/.crush" ]; then
        TOOL="opencode"
    elif [ -d "$HOME/.codex" ]; then
        TOOL="codex"
    elif command -v claude &> /dev/null; then
        TOOL="claude-code"
    else
        TOOL="claude-code"
    fi
}

# 设置工具目录
setup_tool_dirs() {
    case "$TOOL" in
        claude-code)
            CONFIG_DIR="$HOME/.claude"
            CONTEXT_FILE="CLAUDE.md"
            ;;
        opencode|crush)
            CONFIG_DIR="$HOME/.opencode"
            CONTEXT_FILE="opencode.md"
            ;;
        codex)
            CONFIG_DIR="$HOME/.codex"
            CONTEXT_FILE="CODEX.md"
            ;;
        copilot)
            CONFIG_DIR="$HOME/.copilot"
            CONTEXT_FILE="COPILOT.md"
            ;;
        *)
            echo -e "${RED}Unknown tool: $TOOL${NC}"
            echo "Supported tools: claude-code, opencode, codex, copilot"
            exit 1
            ;;
    esac

    MEMORY_DIR="$CONFIG_DIR/memory"
    MEMORIES_DIR="$MEMORY_DIR/memories"
    QDRANT_DIR="$MEMORY_DIR/qdrant"
    OBSERVATIONS_DIR="$CONFIG_DIR/observations"
    INSTINCTS_DIR="$CONFIG_DIR/homunculus/instincts/personal"
    RULES_DIR="$CONFIG_DIR/rules"
}

# 检查 Python
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON="python3"
    elif command -v python &> /dev/null; then
        PYTHON="python"
    else
        echo -e "${RED}Error: Python not found. Please install Python 3.8+${NC}"
        exit 1
    fi
}

# 创建目录
create_dirs() {
    echo -e "${YELLOW}Step 1/5${NC} Creating directories for ${BLUE}$TOOL${NC}..."
    mkdir -p "$CONFIG_DIR/hooks"
    mkdir -p "$CONFIG_DIR/bin"
    mkdir -p "$OBSERVATIONS_DIR"
    mkdir -p "$INSTINCTS_DIR"
    mkdir -p "$MEMORIES_DIR"
    mkdir -p "$QDRANT_DIR"
    mkdir -p "$RULES_DIR"
}

# 下载脚本
download_scripts() {
    echo -e "${YELLOW}Step 2/5${NC} Downloading scripts..."

    curl -fsSL "$REPO_URL/hooks/observe.py" -o "$CONFIG_DIR/hooks/observe.py"
    curl -fsSL "$REPO_URL/bin/auto-analyze-instincts.py" -o "$CONFIG_DIR/bin/auto-analyze-instincts.py"
    curl -fsSL "$REPO_URL/bin/auto-evolve.py" -o "$CONFIG_DIR/bin/auto-evolve.py"
    curl -fsSL "$REPO_URL/bin/inject_memory_context.py" -o "$CONFIG_DIR/bin/inject_memory_context.py"
    curl -fsSL "$REPO_URL/bin/observations_rotate.py" -o "$CONFIG_DIR/bin/observations_rotate.py"
}

# 安装依赖
install_deps() {
    echo -e "${YELLOW}Step 3/5${NC} Installing Python dependencies..."
    $PYTHON -m pip install -q qdrant-client sentence-transformers 2>/dev/null || {
        $PYTHON -m pip install qdrant-client sentence-transformers
    }
}

# 配置 hooks（仅 Claude Code）
configure_hooks() {
    if [ "$TOOL" != "claude-code" ]; then
        echo -e "${YELLOW}Step 4/5${NC} Skipping hooks configuration (not supported by $TOOL)..."
        echo -e "  ${BLUE}Note: $TOOL does not support hooks. Only static memory files will be available.${NC}"
        return
    fi

    echo -e "${YELLOW}Step 4/5${NC} Configuring hooks..."

    SETTINGS_FILE="$CONFIG_DIR/settings.json"
    if [ -f "$SETTINGS_FILE" ]; then
        cp "$SETTINGS_FILE" "$SETTINGS_FILE.backup.$(date +%Y%m%d%H%M%S)"
    fi

    cat > /tmp/merge_settings.py << 'PYEOF'
import json
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
PYEOF

    $PYTHON /tmp/merge_settings.py
    rm /tmp/merge_settings.py
}

# 创建示例记忆
create_example_memory() {
    echo -e "${YELLOW}Step 5/5${NC} Creating example memory..."

    EXAMPLE_MEMORY="$MEMORIES_DIR/getting-started.md"
    cat > "$EXAMPLE_MEMORY" << EOF
---
name: getting-started
description: 快速入门指南
metadata:
  type: reference
---

## Claude Code Memory System 已安装！

工具: $TOOL

### 功能说明

$(if [ "$TOOL" = "claude-code" ]; then
echo "- ✅ 完整 Hooks 支持（行为观测 + 自动学习）"
echo "- ✅ 向量检索记忆"
echo "- ✅ Instinct 规则演化"
else
echo "- ⚠️  $TOOL 不支持 Hooks"
echo "- ✅ 静态记忆文件支持"
echo "- ✅ 向量检索记忆"
fi)

### 下一步
1. 重启 $TOOL 开始使用
2. 在 \`$MEMORIES_DIR/\` 添加自定义记忆
3. $(if [ "$TOOL" = "claude-code" ]; then echo "正常使用，系统会自动学习行为模式"; else echo "记忆将在下次启动时加载"; fi)

### 记忆类型
- \`user\`: 用户偏好、身份认知
- \`feedback\`: 纠正和指导
- \`project\`: 项目上下文
- \`reference\`: 外部资源引用
EOF
}

# 打印完成信息
print_done() {
    echo ""
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              Installation Complete!                       ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "Tool: ${YELLOW}$TOOL${NC}"
    echo -e "Config: ${YELLOW}$CONFIG_DIR${NC}"
    echo ""

    if [ "$TOOL" = "claude-code" ]; then
        echo -e "${GREEN}Full features enabled:${NC}"
        echo "  ✅ Observation hooks"
        echo "  ✅ Instinct evolution"
        echo "  ✅ Vector memory"
    else
        echo -e "${BLUE}Limited features (no hooks support):${NC}"
        echo "  ✅ Static memory files"
        echo "  ✅ Vector memory"
        echo "  ❌ Observation hooks (not supported)"
        echo "  ❌ Instinct evolution (not supported)"
    fi

    echo ""
    echo -e "Next steps:"
    echo -e "  1. ${YELLOW}Restart $TOOL${NC} to activate"
    echo -e "  2. Add memories to ${YELLOW}$MEMORIES_DIR/${NC}"
    echo ""
}

# 主流程
main() {
    detect_tool
    setup_tool_dirs
    check_python
    create_dirs
    download_scripts
    install_deps
    configure_hooks
    create_example_memory
    print_done
}

main "$@"

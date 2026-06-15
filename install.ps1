# Claude Code Memory System - Windows 一键安装脚本
# 用法: irm https://raw.githubusercontent.com/ziyouvip/claude-code-memory-system/main/install.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║     Claude Code Memory System - Installer                 ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

$CLAUDE_DIR = "$env:USERPROFILE\.claude"
$REPO_URL = "https://raw.githubusercontent.com/ziyouvip/claude-code-memory-system/main"

# Step 1: 创建目录
Write-Host "Step 1/5 Creating directories..." -ForegroundColor Yellow
$dirs = @(
    "$CLAUDE_DIR\hooks",
    "$CLAUDE_DIR\bin",
    "$CLAUDE_DIR\observations",
    "$CLAUDE_DIR\homunculus\instincts\personal",
    "$CLAUDE_DIR\memory\memories",
    "$CLAUDE_DIR\memory\qdrant",
    "$CLAUDE_DIR\rules"
)
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

# Step 2: 下载脚本
Write-Host "Step 2/5 Downloading scripts..." -ForegroundColor Yellow
$files = @(
    @{Url = "$REPO_URL/hooks/observe.py"; Path = "$CLAUDE_DIR\hooks\observe.py"},
    @{Url = "$REPO_URL/bin/auto-analyze-instincts.py"; Path = "$CLAUDE_DIR\bin\auto-analyze-instincts.py"},
    @{Url = "$REPO_URL/bin/auto-evolve.py"; Path = "$CLAUDE_DIR\bin\auto-evolve.py"},
    @{Url = "$REPO_URL/bin/inject_memory_context.py"; Path = "$CLAUDE_DIR\bin\inject_memory_context.py"},
    @{Url = "$REPO_URL/bin/observations_rotate.py"; Path = "$CLAUDE_DIR\bin\observations_rotate.py"}
)
foreach ($file in $files) {
    Invoke-WebRequest -Uri $file.Url -OutFile $file.Path -UseBasicParsing
}

# Step 3: 安装 Python 依赖
Write-Host "Step 3/5 Installing Python dependencies..." -ForegroundColor Yellow
pip install qdrant-client sentence-transformers -q 2>$null
if ($LASTEXITCODE -ne 0) {
    pip install qdrant-client sentence-transformers
}

# Step 4: 配置 hooks
Write-Host "Step 4/5 Configuring hooks..." -ForegroundColor Yellow
$settingsFile = "$CLAUDE_DIR\settings.json"

if (Test-Path $settingsFile) {
    Copy-Item $settingsFile "$settingsFile.backup.$(Get-Date -Format 'yyyyMMddHHmmss')"
    $settings = Get-Content $settingsFile | ConvertFrom-Json
} else {
    $settings = @{}
}

$hooksConfig = @{
    PreToolUse = @(
        @{
            matcher = "Bash"
            hooks = @(@{type = "command"; command = "python ~/.claude/hooks/observe.py pre"})
        }
    )
    PostToolUse = @(
        @{
            matcher = ".*"
            hooks = @(@{type = "command"; command = "python ~/.claude/hooks/observe.py post"})
        }
    )
    Stop = @(
        @{
            hooks = @(@{type = "command"; command = "python ~/.claude/bin/auto-analyze-instincts.py && python ~/.claude/bin/auto-evolve.py"})
        }
    )
    SessionStart = @(
        @{
            hooks = @(@{type = "command"; command = "python ~/.claude/bin/inject_memory_context.py"})
        }
    )
}

# 添加 hooks 到 settings
$settings | Add-Member -NotePropertyName "hooks" -NotePropertyValue $hooksConfig -Force
$settings | ConvertTo-Json -Depth 10 | Set-Content $settingsFile

# Step 5: 创建示例记忆
Write-Host "Step 5/5 Creating example memory..." -ForegroundColor Yellow
$exampleMemory = @"
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
在 ``~/.claude/memory/memories/`` 目录下创建 ``.md`` 文件来添加记忆。
"@
$exampleMemory | Out-File -FilePath "$CLAUDE_DIR\memory\memories\getting-started.md" -Encoding utf8

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              Installation Complete!                       ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Installed to: $CLAUDE_DIR" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. " -NoNewline; Write-Host "Restart Claude Code" -ForegroundColor Yellow -NoNewline; Write-Host " to activate the system"
Write-Host "  2. Use Claude Code normally - your behavior will be learned"
Write-Host "  3. Add custom memories to " -NoNewline; Write-Host "~/.claude/memory/memories/" -ForegroundColor Yellow
Write-Host ""

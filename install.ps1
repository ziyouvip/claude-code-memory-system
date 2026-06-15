# Claude Code Memory System - Windows 一键安装脚本
# 用法: irm https://raw.githubusercontent.com/ziyouvip/claude-code-memory-system/master/install.ps1 | iex

$ErrorActionPreference = "Stop"

Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║     Claude Code Memory System - Installer                 ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""

$REPO_URL = "https://raw.githubusercontent.com/ziyouvip/claude-code-memory-system/master"

# 默认工具
$Tool = if ($env:TOOL) { $env:TOOL } else { "claude-code" }

# 设置工具目录
switch ($Tool) {
    "claude-code" {
        $ConfigDir = "$env:USERPROFILE\.claude"
        $ContextFile = "CLAUDE.md"
    }
    "opencode" {
        $ConfigDir = "$env:USERPROFILE\.opencode"
        $ContextFile = "opencode.md"
    }
    "codex" {
        $ConfigDir = "$env:USERPROFILE\.codex"
        $ContextFile = "CODEX.md"
    }
    "copilot" {
        $ConfigDir = "$env:USERPROFILE\.copilot"
        $ContextFile = "COPILOT.md"
    }
    default {
        Write-Host "Unknown tool: $Tool" -ForegroundColor Red
        Write-Host "Supported tools: claude-code, opencode, codex, copilot"
        exit 1
    }
}

$MemoryDir = "$ConfigDir\memory"
$MemoriesDir = "$MemoryDir\memories"
$QdrantDir = "$MemoryDir\qdrant"
$ObservationsDir = "$ConfigDir\observations"
$InstinctsDir = "$ConfigDir\homunculus\instincts\personal"
$RulesDir = "$ConfigDir\rules"

# Step 1: 创建目录
Write-Host "Step 1/5 Creating directories for $Tool..." -ForegroundColor Yellow
$dirs = @(
    "$ConfigDir\hooks",
    "$ConfigDir\bin",
    $ObservationsDir,
    $InstinctsDir,
    $MemoriesDir,
    $QdrantDir,
    $RulesDir
)
foreach ($dir in $dirs) {
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
}

# Step 2: 下载脚本
Write-Host "Step 2/5 Downloading scripts..." -ForegroundColor Yellow
$files = @(
    @{Url = "$REPO_URL/hooks/observe.py"; Path = "$ConfigDir\hooks\observe.py"},
    @{Url = "$REPO_URL/bin/auto-analyze-instincts.py"; Path = "$ConfigDir\bin\auto-analyze-instincts.py"},
    @{Url = "$REPO_URL/bin/auto-evolve.py"; Path = "$ConfigDir\bin\auto-evolve.py"},
    @{Url = "$REPO_URL/bin/inject_memory_context.py"; Path = "$ConfigDir\bin\inject_memory_context.py"},
    @{Url = "$REPO_URL/bin/observations_rotate.py"; Path = "$ConfigDir\bin\observations_rotate.py"}
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

# Step 4: 配置 hooks（仅 Claude Code）
if ($Tool -eq "claude-code") {
    Write-Host "Step 4/5 Configuring hooks..." -ForegroundColor Yellow
    $settingsFile = "$ConfigDir\settings.json"

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

    $settings | Add-Member -NotePropertyName "hooks" -NotePropertyValue $hooksConfig -Force
    $settings | ConvertTo-Json -Depth 10 | Set-Content $settingsFile
} else {
    Write-Host "Step 4/5 Skipping hooks (not supported by $Tool)..." -ForegroundColor Yellow
    Write-Host "  Note: $Tool does not support hooks. Only static memory files available." -ForegroundColor Cyan
}

# Step 5: 创建示例记忆
Write-Host "Step 5/5 Creating example memory..." -ForegroundColor Yellow

$hooksNote = if ($Tool -eq "claude-code") {
    "- Full Hooks support (observation + auto-learning)
- Vector memory
- Instinct evolution"
} else {
    "- Static memory files
- Vector memory
- Note: $Tool does not support hooks"
}

$nextSteps = if ($Tool -eq "claude-code") {
    "3. Use normally, system will learn behavior patterns"
} else {
    "3. Memory will be loaded on next start"
}

$exampleMemory = @"
---
name: getting-started
description: 快速入门指南
metadata:
  type: reference
---

## Claude Code Memory System 已安装！

Tool: $Tool

### 功能说明
$hooksNote

### 下一步
1. Restart $Tool to activate
2. Add memories to ``$MemoriesDir\``
$nextSteps

### 记忆类型
- ``user``: 用户偏好、身份认知
- ``feedback``: 纠正和指导
- ``project``: 项目上下文
- ``reference``: 外部资源引用
"@
$exampleMemory | Out-File -FilePath "$MemoriesDir\getting-started.md" -Encoding utf8

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║              Installation Complete!                       ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "Tool: $Tool" -ForegroundColor Yellow
Write-Host "Config: $ConfigDir" -ForegroundColor Yellow
Write-Host ""

if ($Tool -eq "claude-code") {
    Write-Host "Full features enabled:" -ForegroundColor Green
    Write-Host "  [OK] Observation hooks"
    Write-Host "  [OK] Instinct evolution"
    Write-Host "  [OK] Vector memory"
} else {
    Write-Host "Limited features (no hooks support):" -ForegroundColor Cyan
    Write-Host "  [OK] Static memory files"
    Write-Host "  [OK] Vector memory"
    Write-Host "  [X]  Observation hooks (not supported)"
    Write-Host "  [X]  Instinct evolution (not supported)"
}

Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. " -NoNewline; Write-Host "Restart $Tool" -ForegroundColor Yellow -NoNewline; Write-Host " to activate"
Write-Host "  2. Add memories to " -NoNewline; Write-Host "$MemoriesDir\" -ForegroundColor Yellow
Write-Host ""
Write-Host "To install for a different tool, set TOOL environment variable:"
Write-Host "  `$env:TOOL='opencode'; irm ... | iex" -ForegroundColor Gray
Write-Host ""

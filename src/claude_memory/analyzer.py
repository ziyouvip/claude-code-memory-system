"""
Claude Code Memory System - Analyzer Module
"""

import json
import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

CLAUDE_DIR = Path.home() / ".claude"
OBSERVATIONS_FILE = CLAUDE_DIR / "observations" / "observations.jsonl"
INSTINCTS_DIR = CLAUDE_DIR / "homunculus" / "instincts" / "personal"

PATTERNS = {
    "read-before-edit": {
        "trigger": "when about to edit a file that hasn't been read in this session",
        "action": "Use Read tool to read the file content before editing.",
        "domain": "workflow",
    },
    "test-after-change": {
        "trigger": "after making code changes to a project with tests",
        "action": "Run the test suite to verify changes.",
        "domain": "testing",
    },
    "git-status-check": {
        "trigger": "before starting significant work on a git-tracked project",
        "action": "Check git status to understand current state.",
        "domain": "git",
    },
    "install-before-use": {
        "trigger": "before using a CLI tool that may not be installed",
        "action": "Check if the tool exists, and install it if needed.",
        "domain": "workflow",
    },
    "context-gather": {
        "trigger": "before making large-scale changes to a codebase",
        "action": "Gather context by reading key files first.",
        "domain": "workflow",
    },
}


def analyze_observations(verbose: bool = True) -> dict:
    """
    Analyze observations and extract patterns.

    Returns:
        Dict with analysis results
    """
    observations = _load_observations()
    if not observations:
        if verbose:
            print("No observations to analyze")
        return {"patterns": {}, "total_observations": 0}

    pattern_counts = _detect_patterns(observations)

    if verbose:
        print(f"📊 Analyzed {len(observations)} observations")
        print(f"🔍 Detected patterns: {pattern_counts}")

    return {
        "patterns": pattern_counts,
        "total_observations": len(observations),
    }


def evolve_instincts(verbose: bool = True) -> int:
    """
    Evolve instincts from observations.

    Returns:
        Number of instincts created/updated
    """
    observations = _load_observations()
    if not observations:
        if verbose:
            print("No observations to analyze")
        return 0

    pattern_counts = _detect_patterns(observations)
    existing = _get_existing_instincts()
    created = 0

    for pattern_id, count in pattern_counts.items():
        if pattern_id not in PATTERNS:
            continue

        pattern_data = PATTERNS[pattern_id]

        if pattern_id in existing:
            _update_instinct_confidence(existing[pattern_id], 0.05)
            if verbose:
                print(f"  📈 Updated confidence for {pattern_id}")
        else:
            confidence = min(0.9, 0.5 + count * 0.05)
            _create_instinct_file(pattern_id, pattern_data, confidence)
            created += 1
            if verbose:
                print(f"  ✨ Created instinct: {pattern_id}")

    if verbose:
        print(f"\n✅ Created {created} new instincts")

    return created


def _load_observations() -> list[dict]:
    """Load observations from file."""
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


def _detect_patterns(observations: list[dict]) -> dict[str, int]:
    """Detect patterns from observations."""
    pattern_counts = defaultdict(int)
    sessions = defaultdict(list)

    for obs in observations:
        sessions[obs.get("session_id", "unknown")].append(obs)

    for session_id, session_obs in sessions.items():
        session_obs.sort(key=lambda x: x.get("ts", ""))

        # read-before-edit
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

        # test-after-change
        has_edit = False
        for obs in session_obs:
            if obs.get("tool") in ("Edit", "Write"):
                has_edit = True
            elif has_edit and obs.get("tool") == "Bash":
                cmd = obs.get("input", {}).get("command", "")
                if any(kw in cmd for kw in ["test", "vitest", "jest", "pytest"]):
                    pattern_counts["test-after-change"] += 1
                    break

        # context-gather
        read_count = sum(1 for obs in session_obs if obs.get("tool") == "Read")
        edit_count = sum(1 for obs in session_obs if obs.get("tool") in ("Edit", "Write"))
        if read_count >= 3 and edit_count > 0:
            pattern_counts["context-gather"] += 1

    return dict(pattern_counts)


def _get_existing_instincts() -> dict[str, dict]:
    """Load existing instincts."""
    instincts = {}
    if not INSTINCTS_DIR.exists():
        return instincts

    for file_path in INSTINCTS_DIR.glob("*.md"):
        try:
            content = file_path.read_text(encoding="utf-8")
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


def _create_instinct_file(pattern_id: str, pattern_data: dict, confidence: float):
    """Create instinct file."""
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
Detected through statistical pattern analysis.
"""
    file_path.write_text(content, encoding="utf-8")


def _update_instinct_confidence(instinct: dict, delta: float):
    """Update instinct confidence."""
    fm = instinct["frontmatter"]
    current = float(fm.get("confidence", 0.5))
    new_confidence = max(0.0, min(0.9, current + delta))

    fm["confidence"] = f"{new_confidence:.2f}"
    fm["deprecated"] = "false" if new_confidence >= 0.55 else "true"

    frontmatter_str = "\n".join(f"{k}: {v}" for k, v in fm.items())
    content = f"---\n{frontmatter_str}\n---\n\n{instinct['content']}"

    instinct["path"].write_text(content, encoding="utf-8")

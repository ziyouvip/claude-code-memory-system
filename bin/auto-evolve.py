#!/usr/bin/env python3
"""
Instinct 聚合引擎
会话结束时运行，将高置信度 Instinct 聚合成 Evolved Skill
"""

import json
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Optional

# 配置路径
CLAUDE_DIR = Path.home() / ".claude"
INSTINCTS_DIR = CLAUDE_DIR / "homunculus" / "instincts" / "personal"
RULES_DIR = CLAUDE_DIR / "rules"
AUTO_EVOLVED_FILE = RULES_DIR / "auto-evolved.md"

# Jaccard 相似度阈值
SIM_THRESHOLD = 0.5


def tokenize(text: str) -> set[str]:
    """提取英文关键词（用于Jaccard相似度计算）"""
    # 提取英文单词
    words = re.findall(r"[a-zA-Z]{2,}", text.lower())
    return set(words)


def jaccard(set1: set[str], set2: set[str]) -> float:
    """计算Jaccard相似度"""
    if not set1 or not set2:
        return 0.0
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    return intersection / union if union > 0 else 0.0


class UnionFind:
    """并查集数据结构，用于去重"""

    def __init__(self, n: int):
        self.parent = list(range(n))
        self.rank = [0] * n

    def find(self, x: int) -> int:
        if self.parent[x] != x:
            self.parent[x] = self.find(self.parent[x])
        return self.parent[x]

    def union(self, x: int, y: int):
        px, py = self.find(x), self.find(y)
        if px == py:
            return
        if self.rank[px] < self.rank[py]:
            px, py = py, px
        self.parent[py] = px
        if self.rank[px] == self.rank[py]:
            self.rank[px] += 1


def load_instincts() -> list[dict]:
    """加载所有Instinct"""
    instincts = []
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

                    # 跳过 deprecated 的
                    if frontmatter.get("deprecated", "false").lower() == "true":
                        continue

                    instincts.append(
                        {
                            "id": frontmatter.get("id", file_path.stem),
                            "trigger": frontmatter.get("trigger", ""),
                            "action": "",
                            "confidence": float(frontmatter.get("confidence", 0.5)),
                            "domain": frontmatter.get("domain", "workflow"),
                            "content": parts[2].strip(),
                        }
                    )
        except Exception:
            continue

    return instincts


def extract_action(content: str) -> str:
    """从content中提取Action部分"""
    if "## Action" in content:
        parts = content.split("## Action", 1)
        if len(parts) > 1:
            action = parts[1].split("##")[0].strip()
            return action
    return content[:200]


def deduplicate_instincts(instincts: list[dict]) -> list[dict]:
    """基于Jaccard相似度去重"""
    if not instincts:
        return []

    n = len(instincts)
    tokens = [tokenize(i["trigger"] + " " + i.get("action", "")) for i in instincts]
    uf = UnionFind(n)

    for i in range(n):
        for j in range(i + 1, n):
            if jaccard(tokens[i], tokens[j]) >= SIM_THRESHOLD:
                uf.union(i, j)

    # 按组聚合
    groups = defaultdict(list)
    for i in range(n):
        groups[uf.find(i)].append(instincts[i])

    # 每组取置信度最高的
    result = []
    for group in groups.values():
        best = max(group, key=lambda x: x["confidence"])
        result.append(best)

    return result


def aggregate_by_domain(instincts: list[dict]) -> dict[str, list[dict]]:
    """按domain分组"""
    domains = defaultdict(list)
    for instinct in instincts:
        domains[instinct["domain"]].append(instinct)
    return dict(domains)


def generate_evolved_rule(instincts: list[dict], domain: str) -> str:
    """生成单个domain的evolved规则"""
    lines = [f"## {domain.title()} Rules\n"]

    for instinct in instincts:
        action = extract_action(instinct.get("content", ""))
        if not action:
            action = instinct.get("trigger", "")

        lines.append(f"- **{instinct['trigger']}**")
        lines.append(f"  - {action}")
        lines.append(f"  - Confidence: {instinct['confidence']:.0%}\n")

    return "\n".join(lines)


def generate_auto_evolved_md(domains: dict[str, list[dict]]) -> str:
    """生成完整的 auto-evolved.md"""
    lines = [
        "# Auto-Evolved Rules",
        "",
        f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*",
        "",
        "These rules are automatically extracted from observed behavioral patterns.",
        "They are loaded at session start and guide Claude's behavior.",
        "",
    ]

    # 按 domain 排序
    for domain in sorted(domains.keys()):
        instincts = domains[domain]
        if len(instincts) >= 1:  # 至少1条才生成
            lines.append(generate_evolved_rule(instincts, domain))

    return "\n".join(lines)


def main():
    # 加载所有 instincts
    instincts = load_instincts()
    if not instincts:
        print("No instincts to evolve")
        # 创建空的 auto-evolved.md
        RULES_DIR.mkdir(parents=True, exist_ok=True)
        AUTO_EVOLVED_FILE.write_text(
            "# Auto-Evolved Rules\n\n*No rules evolved yet*\n",
            encoding="utf-8",
        )
        return

    print(f"Loaded {len(instincts)} instincts")

    # 过滤高置信度
    high_confidence = [i for i in instincts if i["confidence"] >= 0.7]
    print(f"High confidence: {len(high_confidence)}")

    # 去重
    deduped = deduplicate_instincts(high_confidence)
    print(f"After dedup: {len(deduped)}")

    # 按domain聚合
    domains = aggregate_by_domain(deduped)
    print(f"Domains: {list(domains.keys())}")

    # 生成 auto-evolved.md
    content = generate_auto_evolved_md(domains)

    # 确保目录存在
    RULES_DIR.mkdir(parents=True, exist_ok=True)

    # 写入文件
    AUTO_EVOLVED_FILE.write_text(content, encoding="utf-8")
    print(f"Generated {AUTO_EVOLVED_FILE}")

    # 打印摘要
    for domain, insts in sorted(domains.items()):
        print(f"  {domain}: {len(insts)} rules")


if __name__ == "__main__":
    main()

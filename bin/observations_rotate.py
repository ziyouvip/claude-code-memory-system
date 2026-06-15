#!/usr/bin/env python3
"""
观测数据归档脚本
防止数据膨胀，自动按月归档
"""

import gzip
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path

# 配置路径
CLAUDE_DIR = Path.home() / ".claude"
OBSERVATIONS_DIR = CLAUDE_DIR / "observations"
OBSERVATIONS_FILE = OBSERVATIONS_DIR / "observations.jsonl"
ARCHIVE_DIR = OBSERVATIONS_DIR / "archive"

# 阈值
MAX_SIZE_MB = 5
MAX_LINES = 8000
KEEP_DAYS = 30


def get_file_stats(file_path: Path) -> tuple[int, int]:
    """获取文件行数和大小(MB)"""
    if not file_path.exists():
        return 0, 0

    lines = 0
    with open(file_path, "r", encoding="utf-8") as f:
        for _ in f:
            lines += 1

    size_mb = file_path.stat().st_size / (1024 * 1024)
    return lines, size_mb


def parse_observation_date(line: str) -> datetime:
    """解析观测记录的日期"""
    try:
        data = json.loads(line)
        ts = data.get("ts", "")
        if ts:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        pass
    return datetime.now()


def archive_old_observations():
    """归档旧观测数据"""
    if not OBSERVATIONS_FILE.exists():
        return

    lines, size_mb = get_file_stats(OBSERVATIONS_FILE)
    print(f"Current: {lines} lines, {size_mb:.2f} MB")

    # 检查是否需要归档
    if lines < MAX_LINES and size_mb < MAX_SIZE_MB:
        print("No need to archive")
        return

    # 创建归档目录
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    # 按月份分组
    monthly = {}
    cutoff_date = datetime.now() - timedelta(days=KEEP_DAYS)

    with open(OBSERVATIONS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            obs_date = parse_observation_date(line)
            month_key = obs_date.strftime("%Y-%m")

            if month_key not in monthly:
                monthly[month_key] = []
            monthly[month_key].append(line)

    # 归档各月数据
    recent_lines = []

    for month, records in sorted(monthly.items()):
        # 检查是否在保留期内
        month_date = datetime.strptime(month, "%Y-%m")
        is_recent = month_date.replace(day=1) >= cutoff_date.replace(day=1)

        if is_recent:
            # 保留期内，检查每条记录
            for record in records:
                obs_date = parse_observation_date(record)
                if obs_date >= cutoff_date:
                    recent_lines.append(record)
                else:
                    # 归档旧记录
                    archive_file = ARCHIVE_DIR / f"observations-{month}.jsonl.gz"
                    with gzip.open(archive_file, "at", encoding="utf-8") as gz:
                        gz.write(record + "\n")
        else:
            # 超过保留期，全部归档
            archive_file = ARCHIVE_DIR / f"observations-{month}.jsonl.gz"
            with gzip.open(archive_file, "at", encoding="utf-8") as gz:
                for record in records:
                    gz.write(record + "\n")

    # 写回保留的数据
    with open(OBSERVATIONS_FILE, "w", encoding="utf-8") as f:
        for line in recent_lines:
            f.write(line + "\n")

    print(f"Archived. Remaining: {len(recent_lines)} lines")


def cleanup_old_archives():
    """清理超过6个月的归档"""
    if not ARCHIVE_DIR.exists():
        return

    cutoff = datetime.now() - timedelta(days=180)

    for archive_file in ARCHIVE_DIR.glob("observations-*.jsonl.gz"):
        # 从文件名提取月份
        try:
            month_str = archive_file.stem.replace("observations-", "").replace(".jsonl", "")
            month_date = datetime.strptime(month_str, "%Y-%m")
            if month_date < cutoff:
                archive_file.unlink()
                print(f"Deleted old archive: {archive_file.name}")
        except Exception:
            continue


def main():
    archive_old_observations()
    cleanup_old_archives()


if __name__ == "__main__":
    main()

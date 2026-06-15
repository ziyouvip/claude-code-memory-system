#!/usr/bin/env python3
"""
记忆注入系统
会话启动时运行，检索相关记忆并注入上下文
"""

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# 配置路径
CLAUDE_DIR = Path.home() / ".claude"
MEMORY_DIR = CLAUDE_DIR / "memory"
MEMORIES_DIR = MEMORY_DIR / "memories"
QDRANT_DIR = MEMORY_DIR / "qdrant"
MEMORY_INDEX_FILE = CLAUDE_DIR / "MEMORY.md"

# 向量配置
COLLECTION_NAME = "memories"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# 全局变量
embedding_model = None
qdrant_client = None


def init_embedding():
    """初始化embedding模型"""
    global embedding_model
    if embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        except ImportError:
            print("sentence-transformers not installed", file=sys.stderr)
            return None
    return embedding_model


def init_qdrant():
    """初始化Qdrant客户端"""
    global qdrant_client
    if qdrant_client is None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams

            QDRANT_DIR.mkdir(parents=True, exist_ok=True)
            qdrant_client = QdrantClient(path=str(QDRANT_DIR))

            collections = qdrant_client.get_collections().collections
            if not any(c.name == COLLECTION_NAME for c in collections):
                qdrant_client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
        except ImportError:
            print("qdrant-client not installed", file=sys.stderr)
            return None
    return qdrant_client


def embed(text: str) -> list[float]:
    """生成文本向量"""
    model = init_embedding()
    if model is None:
        return []
    return model.encode(text).tolist()


def get_git_commits(cwd: str, count: int = 3) -> str:
    """获取最近的git commit信息"""
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"-{count}"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


def build_query(cwd: str) -> str:
    """构建查询向量"""
    project_name = Path(cwd).name
    commits = get_git_commits(cwd)
    query = f"{project_name}"
    if commits:
        query += f" {commits}"
    return query


def load_memories() -> list[dict]:
    """加载所有记忆文件"""
    memories = []
    if not MEMORIES_DIR.exists():
        return memories

    for file_path in MEMORIES_DIR.glob("*.md"):
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

                    memories.append({
                        "name": frontmatter.get("name", file_path.stem),
                        "type": frontmatter.get("metadata", {}).get("type", "project"),
                        "description": frontmatter.get("description", ""),
                        "content": parts[2].strip(),
                        "path": str(file_path),
                    })
        except Exception:
            continue
    return memories


def recall_memories(query: str, top_k: int = 5) -> list[dict]:
    """向量检索最相关的记忆"""
    client = init_qdrant()
    if client is None:
        return []

    try:
        query_vec = embed(query)
        if not query_vec:
            return []

        results = client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vec,
            limit=top_k,
        )

        memories = load_memories()
        memory_map = {m["name"]: m for m in memories}

        recalled = []
        for hit in results:
            name = hit.payload.get("name", "")
            if name in memory_map:
                mem = memory_map[name].copy()
                mem["score"] = hit.score
                recalled.append(mem)
        return recalled
    except Exception as e:
        print(f"Recall failed: {e}", file=sys.stderr)
        return []


def index_memories():
    """索引所有记忆到向量数据库"""
    client = init_qdrant()
    if client is None:
        return

    memories = load_memories()
    if not memories:
        return

    try:
        from qdrant_client.http.models import PointStruct

        points = []
        for i, mem in enumerate(memories):
            text = f"{mem['name']} {mem['description']} {mem['content'][:200]}"
            vec = embed(text)
            if vec:
                points.append(PointStruct(
                    id=i,
                    vector=vec,
                    payload={"name": mem["name"], "type": mem["type"]},
                ))

        if points:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            print(f"Indexed {len(points)} memories")
    except Exception as e:
        print(f"Index failed: {e}", file=sys.stderr)


def main():
    cwd = os.environ.get("PWD", os.getcwd())
    query = build_query(cwd)
    print(f"Query: {query}")
    index_memories()
    memories = recall_memories(query)
    print(f"Recalled {len(memories)} memories")


if __name__ == "__main__":
    main()

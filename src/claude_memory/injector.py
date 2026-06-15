"""
Claude Code Memory System - Injector Module
"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

CLAUDE_DIR = Path.home() / ".claude"
MEMORIES_DIR = CLAUDE_DIR / "memory" / "memories"
QDRANT_DIR = CLAUDE_DIR / "memory" / "qdrant"
MEMORY_INDEX_FILE = CLAUDE_DIR / "MEMORY.md"

COLLECTION_NAME = "memories"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

_embedding_model = None
_qdrant_client = None


def inject_memories(verbose: bool = True) -> list[dict]:
    """Inject relevant memories into context."""
    _init_embedding()
    _init_qdrant()
    
    cwd = os.environ.get("PWD", os.getcwd())
    query = _build_query(cwd)
    
    if verbose:
        print(f"Query: {query}")
    
    _index_memories(verbose)
    memories = _recall_memories(query)
    
    if verbose:
        print(f"Recalled {len(memories)} memories")
    
    return memories


def _init_embedding():
    global _embedding_model
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL)
        except ImportError:
            pass
    return _embedding_model


def _init_qdrant():
    global _qdrant_client
    if _qdrant_client is None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.http.models import Distance, VectorParams
            
            QDRANT_DIR.mkdir(parents=True, exist_ok=True)
            _qdrant_client = QdrantClient(path=str(QDRANT_DIR))
            
            collections = _qdrant_client.get_collections().collections
            if not any(c.name == COLLECTION_NAME for c in collections):
                _qdrant_client.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=384, distance=Distance.COSINE),
                )
        except ImportError:
            pass
    return _qdrant_client


def _embed(text: str) -> list[float]:
    model = _init_embedding()
    if model is None:
        return []
    return model.encode(text).tolist()


def _build_query(cwd: str) -> str:
    project_name = Path(cwd).name
    try:
        result = subprocess.run(["git", "log", "--oneline", "-3"], cwd=cwd, capture_output=True, text=True, timeout=5)
        commits = result.stdout.strip() if result.returncode == 0 else ""
    except Exception:
        commits = ""
    return f"{project_name} {commits}" if commits else project_name


def _load_memories() -> list[dict]:
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
                        "type": "project",
                        "description": frontmatter.get("description", ""),
                        "content": parts[2].strip(),
                        "path": str(file_path),
                    })
        except Exception:
            continue
    return memories


def _index_memories(verbose: bool = False):
    client = _init_qdrant()
    if client is None:
        return
    
    memories = _load_memories()
    if not memories:
        return
    
    try:
        from qdrant_client.http.models import PointStruct
        
        points = []
        for i, mem in enumerate(memories):
            text = f"{mem['name']} {mem['description']} {mem['content'][:200]}"
            vec = _embed(text)
            if vec:
                points.append(PointStruct(id=i, vector=vec, payload={"name": mem["name"], "type": mem["type"]}))
        
        if points:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            if verbose:
                print(f"Indexed {len(points)} memories")
    except Exception:
        pass


def _recall_memories(query: str, top_k: int = 5) -> list[dict]:
    client = _init_qdrant()
    if client is None:
        return []
    
    try:
        query_vec = _embed(query)
        if not query_vec:
            return []
        
        results = client.search(collection_name=COLLECTION_NAME, query_vector=query_vec, limit=top_k)
        
        memories = _load_memories()
        memory_map = {m["name"]: m for m in memories}
        
        recalled = []
        for hit in results:
            name = hit.payload.get("name", "")
            if name in memory_map:
                mem = memory_map[name].copy()
                mem["score"] = hit.score
                recalled.append(mem)
        return recalled
    except Exception:
        return []

import os
import json
from typing import List, Dict, Any, Optional

import numpy as np

import faiss  # type: ignore


class FaissStore:
    def __init__(self, dim: int, index_path: str, meta_path: str):
        self.dim = dim
        self.index_path = index_path
        self.meta_path = meta_path
        self.index: Optional[faiss.Index] = None
        self.metadatas: List[Dict[str, Any]] = []
        self._load()

    def _create_index(self) -> faiss.Index:
        # Cosine similarity via inner product on L2-normalized vectors
        return faiss.IndexFlatIP(self.dim)

    def _save(self) -> None:
        if self.index is None:
            return
        faiss.write_index(self.index, self.index_path)
        with open(self.meta_path, "w", encoding="utf-8") as f:
            json.dump(self.metadatas, f)

    def _load(self) -> None:
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self.metadatas = json.load(f)
                return
            except Exception:
                # Fall back to new empty index on load failure
                self.index = None
                self.metadatas = []
        # Create empty index
        self.index = self._create_index()
        self.metadatas = []
        self._save()

    def add(self, vectors: np.ndarray, metadatas: List[Dict[str, Any]]):
        if self.index is None:
            self.index = self._create_index()
        # Normalize for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-8
        vectors_norm = (vectors / norms).astype(np.float32)
        self.index.add(vectors_norm)
        self.metadatas.extend(metadatas)
        self._save()

    def search(self, query: np.ndarray, k: int) -> List[Dict[str, Any]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        q = (query / (np.linalg.norm(query) + 1e-8)).astype(np.float32)[None, :]
        _, idxs = self.index.search(q, min(k, self.index.ntotal))
        results: List[Dict[str, Any]] = []
        for i in idxs[0]:
            if 0 <= i < len(self.metadatas):
                results.append(self.metadatas[i])
        return results


INDEX_STATE: Dict[str, Any] = {"store": None, "dim": 768, "dir": None}


def dummy_embed(text: str, dim: int = 768) -> np.ndarray:
    # Deterministic pseudo-embedding (placeholder). Replace with real embeddings.
    rng = np.random.default_rng(abs(hash(text)) % (2**32))
    return rng.normal(0, 1, size=(dim,)).astype(np.float32)


def get_or_create_index(index_dir: str) -> FaissStore:
    os.makedirs(index_dir, exist_ok=True)
    if INDEX_STATE["store"] is None:
        index_path = os.path.join(index_dir, "faiss.index")
        meta_path = os.path.join(index_dir, "metadatas.json")
        INDEX_STATE["store"] = FaissStore(dim=INDEX_STATE["dim"], index_path=index_path, meta_path=meta_path)
        INDEX_STATE["dir"] = index_dir
    return INDEX_STATE["store"]


def upsert_documents(index: FaissStore, docs: List[Dict[str, Any]]):
    vectors = []
    metas = []
    for d in docs:
        text = d.get("text", "")
        vectors.append(dummy_embed(text, dim=index.dim))
        metas.append(d)
    if vectors:
        index.add(np.vstack(vectors), metas)


def search_similar_snippets(index: FaissStore, query_text: str, k: int = 3) -> List[str]:
    q = dummy_embed(query_text, dim=index.dim)
    results = index.search(q, k * 2)  # fetch extras then filter
    snippets: List[str] = []
    for r in results:
        t = r.get("text", "") or ""
        src = (r.get("source") or "").lower()
        if not t.strip():
            continue
        # Skip audio-derived or placeholder artifacts
        if any(src.endswith(ext) for ext in (".webm", ".wav", ".mp3", ".m4a", ".ogg")):
            continue
        if "placeholder" in t.lower():
            continue
        snippets.append(t[:1200])
        if len(snippets) >= k:
            break
    return snippets


def clear_index(index_dir: str) -> None:
    """Delete FAISS index and metadata, and reset in-memory store."""
    try:
        path = os.path.join(index_dir, "faiss.index")
        meta = os.path.join(index_dir, "metadatas.json")
        if os.path.exists(path):
            os.remove(path)
        if os.path.exists(meta):
            os.remove(meta)
    except Exception:
        pass
    INDEX_STATE["store"] = None



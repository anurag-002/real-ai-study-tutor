import os
import json
from typing import List, Dict, Any, Optional

import numpy as np

# Try to import faiss, use fallback if not available
try:
    import faiss
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False
    print("WARNING: FAISS not available, RAG features will use in-memory fallback")

# Lazy-load sentence transformers to avoid blocking worker startup
EMBEDDING_MODEL = None
USE_REAL_EMBEDDINGS = False  # Disabled by default for lighter deployments
EMBEDDING_DIM = 384  # all-MiniLM-L6-v2 dimension


def _get_embedding_model():
    """Lazy-load the sentence transformer model."""
    global EMBEDDING_MODEL, USE_REAL_EMBEDDINGS
    if EMBEDDING_MODEL is None and os.getenv('USE_ML_EMBEDDINGS', 'false').lower() == 'true':
        try:
            from sentence_transformers import SentenceTransformer
            EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')
            USE_REAL_EMBEDDINGS = True
            print("RAG: Loaded real embeddings model")
        except ImportError:
            print("RAG: sentence-transformers not installed, using dummy embeddings")
            USE_REAL_EMBEDDINGS = False
    return EMBEDDING_MODEL


class FaissStore:
    def __init__(self, dim: int, index_path: str, meta_path: str):
        self.dim = dim
        self.index_path = index_path
        self.meta_path = meta_path
        self.index: Optional[Any] = None
        self.metadatas: List[Dict[str, Any]] = []
        self.vectors: List[np.ndarray] = []  # Fallback when no FAISS
        self._load()

    def _create_index(self):
        if HAS_FAISS:
            return faiss.IndexFlatIP(self.dim)
        else:
            return None  # Use in-memory fallback

    def _save(self) -> None:
        if not HAS_FAISS:
            # Save vectors and metadata without FAISS
            try:
                np.save(self.index_path + '.npy', np.array(self.vectors) if self.vectors else np.array([]))
                with open(self.meta_path, "w", encoding="utf-8") as f:
                    json.dump(self.metadatas, f)
            except Exception as e:
                print(f"RAG: Failed to save index: {e}")
            return
            
        if self.index is None:
            return
        try:
            faiss.write_index(self.index, self.index_path)
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump(self.metadatas, f)
        except Exception as e:
            print(f"RAG: Failed to save index: {e}")

    def _load(self) -> None:
        if not HAS_FAISS:
            # Load without FAISS
            npy_path = self.index_path + '.npy'
            if os.path.exists(npy_path) and os.path.exists(self.meta_path):
                try:
                    vectors = np.load(npy_path)
                    self.vectors = list(vectors) if len(vectors) > 0 else []
                    with open(self.meta_path, "r", encoding="utf-8") as f:
                        self.metadatas = json.load(f)
                    print(f"RAG: Loaded index with {len(self.vectors)} vectors (no FAISS)")
                except Exception as e:
                    print(f"RAG: Failed to load index: {e}")
                    self.vectors = []
                    self.metadatas = []
            else:
                self.vectors = []
                self.metadatas = []
            return
            
        if os.path.exists(self.index_path) and os.path.exists(self.meta_path):
            try:
                self.index = faiss.read_index(self.index_path)
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self.metadatas = json.load(f)
                print(f"RAG: Loaded index with {self.index.ntotal} vectors")
                return
            except Exception as e:
                print(f"RAG: Failed to load index: {e}")
                self.index = None
                self.metadatas = []
        # Create empty index
        self.index = self._create_index()
        self.metadatas = []
        self._save()

    def add(self, vectors: np.ndarray, metadatas: List[Dict[str, Any]]):
        if not HAS_FAISS:
            # Fallback without FAISS
            for vec in vectors:
                self.vectors.append(vec)
            self.metadatas.extend(metadatas)
            self._save()
            print(f"RAG: Added {len(metadatas)} documents. Total: {len(self.vectors)} (no FAISS)")
            return
            
        if self.index is None:
            self.index = self._create_index()
        # Normalize for cosine similarity
        norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-8
        vectors_norm = (vectors / norms).astype(np.float32)
        self.index.add(vectors_norm)
        self.metadatas.extend(metadatas)
        self._save()
        print(f"RAG: Added {len(metadatas)} documents. Total: {self.index.ntotal}")

    def search(self, query: np.ndarray, k: int) -> List[Dict[str, Any]]:
        if not HAS_FAISS:
            # Fallback search without FAISS - simple cosine similarity
            if not self.vectors:
                return []
            vectors_array = np.array(self.vectors)
            # Normalize query
            q = query / (np.linalg.norm(query) + 1e-8)
            # Compute cosine similarity
            similarities = np.dot(vectors_array, q)
            # Get top k
            top_indices = np.argsort(similarities)[::-1][:k]
            results = []
            for idx in top_indices:
                if 0 <= idx < len(self.metadatas):
                    result = self.metadatas[idx].copy()
                    result['score'] = float(similarities[idx])
                    results.append(result)
            return results
            
        if self.index is None or self.index.ntotal == 0:
            return []
        q = (query / (np.linalg.norm(query) + 1e-8)).astype(np.float32)[None, :]
        scores, idxs = self.index.search(q, min(k, self.index.ntotal))
        results: List[Dict[str, Any]] = []
        for i, score in zip(idxs[0], scores[0]):
            if 0 <= i < len(self.metadatas):
                result = self.metadatas[i].copy()
                result['score'] = float(score)
                results.append(result)
        return results


INDEX_STATE: Dict[str, Any] = {"store": None, "dim": EMBEDDING_DIM, "dir": None}


def get_embedding(text: str) -> np.ndarray:
    """Generate embeddings using sentence-transformers or fallback to dummy."""
    model = _get_embedding_model()
    if USE_REAL_EMBEDDINGS and model:
        try:
            embedding = model.encode(text, convert_to_numpy=True)
            return embedding.astype(np.float32)
        except Exception as e:
            print(f"RAG: Embedding failed, using fallback: {e}")
    
    # Fallback to deterministic pseudo-embedding
    rng = np.random.default_rng(abs(hash(text)) % (2**32))
    return rng.normal(0, 1, size=(INDEX_STATE["dim"],)).astype(np.float32)


def get_or_create_index(index_dir: str) -> FaissStore:
    os.makedirs(index_dir, exist_ok=True)
    if INDEX_STATE["store"] is None:
        index_path = os.path.join(index_dir, "faiss.index")
        meta_path = os.path.join(index_dir, "metadatas.json")
        INDEX_STATE["store"] = FaissStore(dim=INDEX_STATE["dim"], index_path=index_path, meta_path=meta_path)
        INDEX_STATE["dir"] = index_dir
        # Initialize model on first use
        model = _get_embedding_model()
        if USE_REAL_EMBEDDINGS and model:
            print("RAG: Using real embeddings (all-MiniLM-L6-v2)")
        else:
            print("RAG: WARNING - Using dummy embeddings. Install sentence-transformers for better results.")
    return INDEX_STATE["store"]


def upsert_documents(index: FaissStore, docs: List[Dict[str, Any]]):
    """Add documents to the index with real embeddings."""
    if not docs:
        return
    
    vectors = []
    metas = []
    for d in docs:
        text = d.get("text", "")
        if not text or not text.strip():
            continue
        vectors.append(get_embedding(text))
        metas.append(d)
    
    if vectors:
        index.add(np.vstack(vectors), metas)


def search_similar_snippets(index: FaissStore, query_text: str, k: int = 3) -> List[str]:
    """Search for similar text snippets using semantic similarity."""
    q = get_embedding(query_text)
    results = index.search(q, k * 2)  # fetch extras then filter
    snippets: List[str] = []
    
    for r in results:
        t = r.get("text", "") or ""
        src = (r.get("source") or "").lower()
        score = r.get("score", 0.0)
        
        if not t.strip():
            continue
        # Skip audio-derived or placeholder artifacts
        if any(src.endswith(ext) for ext in (".webm", ".wav", ".mp3", ".m4a", ".ogg")):
            continue
        if "placeholder" in t.lower():
            continue
        
        # Only include results with reasonable similarity scores
        if USE_REAL_EMBEDDINGS and score < 0.3:  # Cosine similarity threshold
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
        print("RAG: Index cleared successfully")
    except Exception as e:
        print(f"RAG: Error clearing index: {e}")
    INDEX_STATE["store"] = None




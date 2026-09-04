import os
import pickle
import numpy as np
from typing import List, Dict, Any, Optional
import faiss
from sentence_transformers import SentenceTransformer
import config

class VectorStore:
    """
    Local FAISS Vector Store manager for indexing and searching transcript lines.
    Uses sentence-transformers ('all-MiniLM-L6-v2') for embeddings.
    Supports call_id filtering to scope semantic searches to the active call.
    """

    def __init__(self, index_dir: str = None):
        self.index_dir = index_dir or str(config.FAISS_DIR)
        self.index_file = os.path.join(self.index_dir, "faiss.index")
        self.metadata_file = os.path.join(self.index_dir, "metadata.pkl")

        self.model = SentenceTransformer("all-MiniLM-L6-v2")
        self.dimension = 384
        self.index = None
        self.metadata = []

        self._load_or_create_index()

    def _load_or_create_index(self):
        if os.path.exists(self.index_file) and os.path.exists(self.metadata_file):
            try:
                self.index = faiss.read_index(self.index_file)
                with open(self.metadata_file, "rb") as f:
                    self.metadata = pickle.load(f)
                return
            except Exception as e:
                print(f"[VectorStore] Failed to load existing index ({e}). Creating new index.")

        self.index = faiss.IndexFlatL2(self.dimension)
        self.metadata = []

    def save(self):
        os.makedirs(self.index_dir, exist_ok=True)
        faiss.write_index(self.index, self.index_file)
        with open(self.metadata_file, "wb") as f:
            pickle.dump(self.metadata, f)

    def add_transcript_lines(self, call_id: int, call_title: str, lines: List[Dict[str, Any]]):
        """
        Embeds and indexes a list of transcript lines for a call.
        """
        if not lines:
            return

        texts = []
        metas = []

        for line in lines:
            full_text = f"Line {line['line_number']}: {line['speaker']}: {line['text']}"
            texts.append(full_text)
            metas.append({
                "call_id": call_id,
                "call_title": call_title,
                "line_number": line["line_number"],
                "speaker": line["speaker"],
                "text": line["text"]
            })

        embeddings = self.model.encode(texts, convert_to_numpy=True)
        faiss.normalize_L2(embeddings)

        self.index.add(embeddings)
        self.metadata.extend(metas)
        self.save()

    def search(self, query: str, top_k: int = 5, call_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Performs semantic vector search over indexed transcript lines,
        optionally scoped to a specific call_id.
        """
        if self.index is None or self.index.ntotal == 0:
            return []

        query_vector = self.model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_vector)

        # If filtering by call_id, retrieve more candidates from FAISS to ensure top_k filtered matches
        fetch_k = min(self.index.ntotal, max(top_k * 5, 20) if call_id is not None else top_k)
        distances, indices = self.index.search(query_vector, fetch_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if 0 <= idx < len(self.metadata):
                item = self.metadata[idx].copy()
                if call_id is not None and item.get("call_id") != call_id:
                    continue
                item["score"] = float(round(1.0 / (1.0 + float(dist)), 4))
                results.append(item)
                if len(results) >= top_k:
                    break

        return results

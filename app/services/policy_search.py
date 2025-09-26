# app/services/policy_search.py
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Iterable

import pandas as pd
import numpy as np

from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PointStruct

from app.core.config import settings


@dataclass
class _Cols:
    SERVICE_ID: str = "서비스명"  # 한국어 컬럼명 사용
    SERVICE_NAME: str = "서비스명"
    TAGS: str = "tags"
    SUPPORT: str = "지원내용"
    REQUIREMENT: str = "구비서류"
    URL: str = "URL"
    COMBINED: str = "combined_text"


def _ensure_columns(df: pd.DataFrame) -> None:
    required = {
        _Cols.SERVICE_ID, _Cols.SERVICE_NAME, _Cols.TAGS,
        _Cols.SUPPORT, _Cols.REQUIREMENT, _Cols.URL
    }
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")


def _default_embed_device() -> str:
    # SentenceTransformer device: "cuda" if FW_DEVICE startswith cuda, else "cpu"
    dev = (settings.FW_DEVICE or "cpu").lower()
    return "cuda" if dev.startswith("cuda") else "cpu"


class PolicySearch:
    """
    CSV -> embeddings (SentenceTransformer) -> Qdrant persisted index
    search(query, topk): returns list[dict] with keys matching SearchItem schema.
    """

    def __init__(
        self,
        csv_path: Optional[str] = None,
        qdrant_path: Optional[str] = None,
        embed_model: Optional[str] = None,
        collection_name: str = "gov_services",
        batch_size: int = 256,
    ):
        self.csv_path = csv_path or settings.POLICY_CSV_PATH
        self.qdrant_path = qdrant_path or settings.QDRANT_PATH
        self.embed_model_name = embed_model or settings.EMBED_MODEL
        self.collection = collection_name
        self.batch_size = int(os.getenv("POLICY_INDEX_BATCH", str(batch_size)))

        # Load CSV
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"Policy CSV not found: {self.csv_path}")
        df = pd.read_csv(self.csv_path).fillna("")
        _ensure_columns(df)
        self.df = df.reset_index(drop=True)

        # Compose text with simple weighting: (name + tags)*3 + support + requirement
        self.df[_Cols.COMBINED] = self._compose_texts(self.df)

        # Init embedder
        device = _default_embed_device()
        self.model = SentenceTransformer(self.embed_model_name, device=device)

        # Init Qdrant (persisted)
        os.makedirs(self.qdrant_path, exist_ok=True)
        self.client = QdrantClient(path=str(self.qdrant_path))

        # Ensure collection exists with correct dims
        self._ensure_collection()

    # ---------- public API ----------

    def search(self, query: str, topk: int = None) -> List[Dict[str, Any]]:
        """
        Vector search with simple keyword-aware reranking.
        Returns: list of dicts containing {rank, service_id, service_name, score, tags, support, url}
        """
        if not query or not query.strip():
            return []
        topk = topk or settings.TOPK_DEFAULT
        # embed query
        vec = self.model.encode([query], normalize_embeddings=True)[0].tolist()

        # retrieve >= topk to allow reranking
        limit = max(10, int(topk))
        hits = self.client.search(collection_name=self.collection, query_vector=vec, limit=limit)

        # rerank by simple keyword bonus
        q = query.lower()
        tokens = [t for t in q.replace(",", " ").split() if t]
        def _bonus(payload: Dict[str, Any]) -> float:
            t = (payload.get(_Cols.TAGS, "") or "").lower()
            s = (payload.get(_Cols.SUPPORT, "") or "").lower()
            b = 0.0
            for tok in tokens:
                if tok in t:
                    b += 0.08
                if tok in s:
                    b += 0.04
            return b

        reranked = sorted(hits, key=lambda h: (float(h.score) + _bonus(h.payload)), reverse=True)[:topk]

        results: List[Dict[str, Any]] = []
        for rank, h in enumerate(reranked, start=1):
            p = h.payload or {}
            # tags -> list[str]
            tags_list = [t.strip() for t in str(p.get(_Cols.TAGS, "")).split(",") if t.strip()]
            results.append({
                "rank": rank,
                "service_id": str(p.get(_Cols.SERVICE_ID, "")),
                "service_name": str(p.get(_Cols.SERVICE_NAME, "")),
                "score": float(h.score),
                "tags": tags_list,
                "support": str(p.get(_Cols.SUPPORT, "")),
                "url": str(p.get(_Cols.URL, "")) or None,
            })
        return results

    def rebuild(self) -> None:
        """Drop & rebuild collection from current CSV."""
        self._recreate_collection()
        self._upsert_all()

    # ---------- internal helpers ----------

    def _compose_texts(self, df: pd.DataFrame) -> pd.Series:
        # server.py 방식 참고: (서비스명 + tags) * 3 + 지원내용
        name_plus_tags = (df[_Cols.SERVICE_NAME].astype(str) + " " + df[_Cols.TAGS].astype(str)).str.strip()
        combined = (name_plus_tags + " ").str.cat(name_plus_tags + " ").str.cat(name_plus_tags + " ")
        combined = combined.str.cat(df[_Cols.SUPPORT].astype(str))
        # normalize spaces
        combined = combined.str.replace(r"\s+", " ", regex=True).str.strip()
        return combined

    def _ensure_collection(self) -> None:
        want_dim = self.model.get_sentence_embedding_dimension()
        exists = self._collection_exists()
        if exists:
            try:
                info = self.client.get_collection(self.collection)
                have_dim = int(info.vectors_count) and int(info.config.params.vectors.size)  # type: ignore[attr-defined]
            except Exception:
                have_dim = None
            if have_dim != want_dim:
                # dimension mismatch -> recreate
                self._recreate_collection(want_dim)
                self._upsert_all()
            else:
                # collection present; assume already indexed (no-ops)
                pass
        else:
            self._recreate_collection(want_dim)
            self._upsert_all()

    def _collection_exists(self) -> bool:
        try:
            return self.client.collection_exists(self.collection)
        except Exception:
            # older clients may raise if absent
            try:
                self.client.get_collection(self.collection)
                return True
            except Exception:
                return False

    def _recreate_collection(self, dim: Optional[int] = None) -> None:
        dim = dim or self.model.get_sentence_embedding_dimension()
        self.client.recreate_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=int(dim), distance=Distance.COSINE),
        )

    def _batched(self, iterable: Iterable[Any], n: int) -> Iterable[List[Any]]:
        batch: List[Any] = []
        for x in iterable:
            batch.append(x)
            if len(batch) >= n:
                yield batch
                batch = []
        if batch:
            yield batch

    def _upsert_all(self) -> None:
        texts = self.df[_Cols.COMBINED].tolist()
        # Encode in batches to limit memory
        idxs = list(range(len(texts)))
        for batch_ids in self._batched(idxs, self.batch_size):
            batch_texts = [texts[i] for i in batch_ids]
            embs = self.model.encode(batch_texts, normalize_embeddings=True, show_progress_bar=False)
            # ensure 2D
            if isinstance(embs, list):
                embs = np.asarray(embs)
            points = [
                PointStruct(
                    id=int(i),  # integer ID in Qdrant
                    vector=embs[j].tolist(),
                    payload={
                        _Cols.SERVICE_ID: str(self.df.at[i, _Cols.SERVICE_ID]),
                        _Cols.SERVICE_NAME: str(self.df.at[i, _Cols.SERVICE_NAME]),
                        _Cols.TAGS: str(self.df.at[i, _Cols.TAGS]),
                        _Cols.SUPPORT: str(self.df.at[i, _Cols.SUPPORT]),
                        _Cols.REQUIREMENT: str(self.df.at[i, _Cols.REQUIREMENT]),
                        _Cols.URL: str(self.df.at[i, _Cols.URL]),
                    },
                )
                for j, i in enumerate(batch_ids)
            ]
            self.client.upsert(collection_name=self.collection, points=points)

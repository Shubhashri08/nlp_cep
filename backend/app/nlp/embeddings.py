"""Dense semantic embeddings via Latent Semantic Analysis (TF-IDF → TruncatedSVD, 64 dimensions).

Fitted on the classifier training corpus plus stored complaints, so vectors share vocabulary with real data.
Used for semantic search and near-duplicate detection. (A transformer encoder could be swapped in behind
the same encode() interface; LSA keeps the system CPU-only and dependency-light.)
"""
import logging
import os
import pickle
from typing import List, Optional

import numpy as np
import sklearn
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer

from backend.app.core.config import settings
from backend.app.nlp.cleaner import normalize_multilingual_text
from backend.app.nlp.corpus import generate_training_corpus

logger = logging.getLogger("urban_planning_dss")

EMBEDDING_MODEL_NAME = "tfidf-lsa-64d"


class DenseEmbeddingEngine:
    def __init__(self, embedding_dim: int = 64, model_dir: Optional[str] = None):
        self.embedding_dim = embedding_dim
        self.model_name = EMBEDDING_MODEL_NAME
        self.model_dir = model_dir or settings.MODELS_DIR
        self.artifact_path = os.path.join(self.model_dir, f"embeddings_{EMBEDDING_MODEL_NAME}.pkl")
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.svd: Optional[TruncatedSVD] = None
        self.explained_variance: float = 0.0

    def load_or_fit(self, extra_texts: Optional[List[str]] = None) -> "DenseEmbeddingEngine":
        if os.path.exists(self.artifact_path):
            try:
                with open(self.artifact_path, "rb") as f:
                    data = pickle.load(f)
                if data.get("sklearn_version") == sklearn.__version__:
                    self.vectorizer, self.svd = data["vectorizer"], data["svd"]
                    self.explained_variance = data.get("explained_variance", 0.0)
                    return self
            except Exception as exc:
                logger.warning("Could not load embeddings artifact (%s); refitting.", exc)
        self.fit(extra_texts or [])
        return self

    def fit(self, extra_texts: List[str]) -> dict:
        texts = [t for t, _ in generate_training_corpus()] + list(extra_texts)
        docs = [normalize_multilingual_text(t) for t in texts]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True, max_features=15000)
        X = self.vectorizer.fit_transform(docs)
        dim = min(self.embedding_dim, X.shape[1] - 1)
        self.svd = TruncatedSVD(n_components=dim, random_state=42)
        self.svd.fit(X)
        self.explained_variance = float(self.svd.explained_variance_ratio_.sum())
        os.makedirs(self.model_dir, exist_ok=True)
        with open(self.artifact_path, "wb") as f:
            pickle.dump({"vectorizer": self.vectorizer, "svd": self.svd, "explained_variance": self.explained_variance,
                         "sklearn_version": sklearn.__version__, "documents": len(docs)}, f)
        return {"dimensions": dim, "documents": len(docs), "explained_variance": round(self.explained_variance, 4)}

    @property
    def dimensions(self) -> int:
        return int(self.svd.n_components) if self.svd is not None else self.embedding_dim

    def encode(self, text: str) -> List[float]:
        if not text or not text.strip():
            return [0.0] * self.dimensions
        dense = self.svd.transform(self.vectorizer.transform([normalize_multilingual_text(text)]))[0]
        norm = np.linalg.norm(dense)
        if norm > 0:
            dense = dense / norm
        return [round(float(x), 6) for x in dense]

    def encode_many(self, texts: List[str]) -> np.ndarray:
        dense = self.svd.transform(self.vectorizer.transform([normalize_multilingual_text(t) for t in texts]))
        norms = np.linalg.norm(dense, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return dense / norms

    @staticmethod
    def compute_similarity(vec1, vec2) -> float:
        v1, v2 = np.asarray(vec1, dtype=float), np.asarray(vec2, dtype=float)
        if v1.shape != v2.shape:
            return 0.0
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        if n1 == 0 or n2 == 0:
            return 0.0
        return float(np.clip(np.dot(v1, v2) / (n1 * n2), -1.0, 1.0))


_engine: Optional[DenseEmbeddingEngine] = None


def get_embedding_engine() -> DenseEmbeddingEngine:
    global _engine
    if _engine is None:
        _engine = DenseEmbeddingEngine().load_or_fit()
    return _engine


def reset_embedding_engine() -> None:
    global _engine
    _engine = None

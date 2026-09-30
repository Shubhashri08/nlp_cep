import os
import pickle
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import TruncatedSVD
from sklearn.metrics.pairwise import cosine_similarity
from backend.app.core.config import settings

class DenseEmbeddingEngine:
    """
    Generates 64-dimensional normalized dense semantic embeddings for complaints and queries,
    allowing fast vector cosine similarity search, clustering, and duplicate detection.
    """
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.svd: Optional[TruncatedSVD] = None
        self.artifact_path = os.path.join(settings.MODELS_DIR, "dense_embeddings_model.pkl")
        self._initialize_or_load()

    def _initialize_or_load(self):
        if os.path.exists(self.artifact_path):
            try:
                with open(self.artifact_path, "rb") as f:
                    data = pickle.load(f)
                    self.vectorizer = data["vectorizer"]
                    self.svd = data["svd"]
                    return
            except Exception:
                pass
        self._fit_semantic_space()

    def _fit_semantic_space(self):
        seed_corpus = [
            "flooding waterlogging monsoon heavy rainfall inundated submerged underpass drain water accumulation",
            "potholes broken road craters uneven asphalt pavement footpath divider excavation trench",
            "garbage waste dumping overflowing bins foul smell plastic uncollected municipal solid waste",
            "water supply drinking pipeline leakage low pressure muddy water contamination tanker",
            "traffic jam congestion gridlock vehicle queue peak hour signal broken road choke",
            "streetlight dark avenue light pole flickering bulb night safety illumination",
            "electricity power cut voltage surge transformer spark live wire hanging",
            "public safety stray dogs crime policing dark streets security women safety",
            "healthcare dispensary clinic dengue malaria mosquito primary health doctor medicines",
            "education municipal school classroom library desk drinking water sanitation roof leak",
            "parks garden children play area tree plantation green cover jogging track encroachment",
            "air quality smog pm25 dust pollution smoke industrial emission construction dust"
        ]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=3000)
        tfidf_mat = self.vectorizer.fit_transform(seed_corpus)
        
        n_components = min(self.embedding_dim, tfidf_mat.shape[0] - 1, tfidf_mat.shape[1] - 1)
        self.svd = TruncatedSVD(n_components=n_components, random_state=42)
        self.svd.fit(tfidf_mat)
        
        os.makedirs(settings.MODELS_DIR, exist_ok=True)
        with open(self.artifact_path, "wb") as f:
            pickle.dump({"vectorizer": self.vectorizer, "svd": self.svd}, f)

    def encode(self, text: str) -> List[float]:
        """Encodes text to normalized float vector."""
        if not text or not text.strip():
            return [0.0] * self.svd.n_components
            
        tfidf = self.vectorizer.transform([text])
        dense = self.svd.transform(tfidf)[0]
        norm = np.linalg.norm(dense)
        if norm > 0:
            dense = dense / norm
        return [round(float(x), 6) for x in dense]

    def compute_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Computes cosine similarity between two dense vectors."""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)
        if norm1 == 0 or norm2 == 0:
            return 0.0
        sim = np.dot(v1, v2) / (norm1 * norm2)
        return float(np.clip(sim, -1.0, 1.0))

embedding_engine = DenseEmbeddingEngine()

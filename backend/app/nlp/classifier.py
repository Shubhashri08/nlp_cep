"""Multi-label grievance classifier: TF-IDF (word 1–2 grams + char 2–5 grams) → One-vs-Rest Logistic Regression.

Training data comes from backend/app/nlp/corpus.py. Metrics reported:
  * held_out  – 20 % stratified split of the generated corpus
  * gold_set  – hand-written sentences never seen in training (more honest estimate)
"""
import logging
import os
import pickle
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import sklearn
from scipy.sparse import hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.multiclass import OneVsRestClassifier

from backend.app.core.config import settings
from backend.app.nlp.cleaner import normalize_multilingual_text
from backend.app.nlp.corpus import GOLD_SET, generate_training_corpus
from backend.app.nlp.lexicon import CATEGORIES

logger = logging.getLogger("urban_planning_dss")

MODEL_VERSION = "v2.0-tfidf-wordchar-ovr"


class UrbanNLPClassifier:
    def __init__(self, model_dir: Optional[str] = None):
        self.model_version = MODEL_VERSION
        self.model_dir = model_dir or settings.MODELS_DIR
        self.model_path = os.path.join(self.model_dir, f"nlp_classifier_{MODEL_VERSION}.pkl")
        self.word_vec: Optional[TfidfVectorizer] = None
        self.char_vec: Optional[TfidfVectorizer] = None
        self.clf: Optional[OneVsRestClassifier] = None
        self.category_names: List[str] = list(CATEGORIES)
        self.metrics: Dict[str, Any] = {}
        self.trained_at: Optional[str] = None

    # ------------------------------------------------------------------ persistence
    def load_or_train(self) -> "UrbanNLPClassifier":
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    data = pickle.load(f)
                if data.get("sklearn_version") == sklearn.__version__:
                    self.word_vec, self.char_vec, self.clf = data["word_vec"], data["char_vec"], data["classifier"]
                    self.category_names = data["category_names"]
                    self.metrics = data.get("metrics", {})
                    self.trained_at = data.get("trained_at")
                    return self
                logger.warning("Classifier artifact built with scikit-learn %s (running %s); retraining.",
                               data.get("sklearn_version"), sklearn.__version__)
            except Exception as exc:  # corrupted artifact
                logger.warning("Could not load classifier artifact (%s); retraining.", exc)
        self.train()
        return self

    def _save(self):
        os.makedirs(self.model_dir, exist_ok=True)
        with open(self.model_path, "wb") as f:
            pickle.dump({
                "word_vec": self.word_vec, "char_vec": self.char_vec, "classifier": self.clf,
                "category_names": self.category_names, "metrics": self.metrics, "version": self.model_version,
                "trained_at": self.trained_at, "sklearn_version": sklearn.__version__,
            }, f)

    # ------------------------------------------------------------------ training
    def _featurize(self, texts: List[str], fit: bool = False):
        norm = [normalize_multilingual_text(t) for t in texts]
        if fit:
            self.word_vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1, sublinear_tf=True, max_features=20000)
            self.char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True, max_features=40000)
            return hstack([self.word_vec.fit_transform(norm), self.char_vec.fit_transform(norm)]).tocsr()
        return hstack([self.word_vec.transform(norm), self.char_vec.transform(norm)]).tocsr()

    def _binarize(self, labels: List[List[str]]) -> np.ndarray:
        y = np.zeros((len(labels), len(self.category_names)), dtype=int)
        for i, ls in enumerate(labels):
            for lbl in ls:
                y[i, self.category_names.index(lbl)] = 1
        return y

    @staticmethod
    def _scores(y_true: np.ndarray, y_pred: np.ndarray, primary_true: List[str], primary_pred: List[str]) -> Dict[str, float]:
        return {
            "primary_accuracy": round(float(accuracy_score(primary_true, primary_pred)), 4),
            "micro_f1": round(float(f1_score(y_true, y_pred, average="micro", zero_division=0)), 4),
            "macro_f1": round(float(f1_score(y_true, y_pred, average="macro", zero_division=0)), 4),
            "micro_precision": round(float(precision_score(y_true, y_pred, average="micro", zero_division=0)), 4),
            "micro_recall": round(float(recall_score(y_true, y_pred, average="micro", zero_division=0)), 4),
            "samples": int(len(y_true)),
        }

    def _predict_matrix(self, X) -> Tuple[np.ndarray, List[str]]:
        probs = self.clf.predict_proba(X)
        y_pred = (probs >= 0.35).astype(int)
        top = probs.argmax(axis=1)
        y_pred[np.arange(len(top)), top] = 1
        return y_pred, [self.category_names[i] for i in top]

    def train(self, corpus: Optional[List[Tuple[str, List[str]]]] = None) -> Dict[str, Any]:
        corpus = corpus or generate_training_corpus()
        texts = [t for t, _ in corpus]
        labels = [ls for _, ls in corpus]
        primaries = [ls[0] for ls in labels]
        tr_idx, te_idx = train_test_split(np.arange(len(texts)), test_size=0.2, random_state=42, stratify=primaries)

        X_train = self._featurize([texts[i] for i in tr_idx], fit=True)
        y_all = self._binarize(labels)
        self.clf = OneVsRestClassifier(LogisticRegression(C=8.0, max_iter=2000, class_weight="balanced"))
        self.clf.fit(X_train, y_all[tr_idx])

        X_test = self._featurize([texts[i] for i in te_idx])
        yp, pp = self._predict_matrix(X_test)
        held_out = self._scores(y_all[te_idx], yp, [primaries[i] for i in te_idx], pp)

        gold_texts = [t for t, _ in GOLD_SET]
        gold_y = self._binarize([ls for _, ls in GOLD_SET])
        gyp, gpp = self._predict_matrix(self._featurize(gold_texts))
        gold = self._scores(gold_y, gyp, [ls[0] for _, ls in GOLD_SET], gpp)
        # A gold prediction counts as correct if the predicted top label is any of the gold labels
        gold["primary_accuracy_any_label"] = round(float(np.mean([p in ls for p, (_, ls) in zip(gpp, GOLD_SET)])), 4)

        per_class = f1_score(y_all[te_idx], yp, average=None, zero_division=0)
        # Refit on the full corpus for deployment
        X_full = self._featurize(texts, fit=True)
        self.clf = OneVsRestClassifier(LogisticRegression(C=8.0, max_iter=2000, class_weight="balanced"))
        self.clf.fit(X_full, y_all)

        self.trained_at = datetime.now(timezone.utc).isoformat()
        self.metrics = {
            "held_out": held_out,
            "gold_set": gold,
            "per_class_f1_held_out": {c: round(float(s), 4) for c, s in zip(self.category_names, per_class)},
            "training_samples": len(texts),
            "features": "tfidf word(1-2) + char_wb(2-5), multilingual gloss expansion",
        }
        self._save()
        logger.info("Trained classifier %s: held-out micro-F1 %.3f, gold primary acc %.3f",
                    self.model_version, held_out["micro_f1"], gold["primary_accuracy_any_label"])
        return self.metrics

    # ------------------------------------------------------------------ inference
    def predict(self, text: str, threshold: float = 0.35) -> Tuple[str, float, List[Dict[str, Any]]]:
        if not text or not text.strip():
            return "OTHER", 0.0, [{"category": "OTHER", "confidence": 0.0}]
        probs = self.clf.predict_proba(self._featurize([text]))[0]
        order = np.argsort(probs)[::-1]
        cats = []
        for i in order:
            if probs[i] >= threshold or not cats:
                cats.append({"category": self.category_names[i], "confidence": round(float(probs[i]), 4)})
        return cats[0]["category"], cats[0]["confidence"], cats


_classifier: Optional[UrbanNLPClassifier] = None


def get_classifier() -> UrbanNLPClassifier:
    global _classifier
    if _classifier is None:
        _classifier = UrbanNLPClassifier().load_or_train()
    return _classifier

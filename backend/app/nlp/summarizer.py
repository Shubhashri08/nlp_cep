"""Summarisation.

* summarize_single_complaint – short structured headline for one grievance (category · location · time).
* textrank_summary           – extractive summary: TF-IDF sentence graph + PageRank (Mihalcea & Tarau 2004).
* summarize_complaint_cluster – traceable summary of many complaints (extractive, optionally LLM-abstractive).
When an LLM provider is configured, abstractive summaries are generated from the extractive evidence only.
"""
import re
from collections import Counter
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

_SENT_SPLIT = re.compile(r"(?<=[.!?।])\s+(?=[A-Z0-9\"'(ऀ-ॿ])")


def split_sentences(text: str) -> List[str]:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return []
    sents = [s.strip() for s in _SENT_SPLIT.split(text) if len(s.strip()) > 2]
    return sents or [text]


def textrank_summary(text_or_sentences, max_sentences: int = 3, damping: float = 0.85) -> Dict[str, Any]:
    sentences = split_sentences(text_or_sentences) if isinstance(text_or_sentences, str) else list(text_or_sentences)
    sentences = [s for s in sentences if len(s.split()) >= 3] or sentences
    if len(sentences) <= max_sentences:
        return {"summary": " ".join(sentences), "sentences": sentences, "scores": [1.0] * len(sentences)}
    try:
        tfidf = TfidfVectorizer(stop_words="english", sublinear_tf=True).fit_transform(sentences)
    except ValueError:  # all stop words
        return {"summary": " ".join(sentences[:max_sentences]), "sentences": sentences[:max_sentences], "scores": []}
    sim = (tfidf @ tfidf.T).toarray()
    np.fill_diagonal(sim, 0.0)
    row_sums = sim.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    transition = sim / row_sums
    n = len(sentences)
    scores = np.ones(n) / n
    for _ in range(100):
        new = (1 - damping) / n + damping * transition.T @ scores
        if np.abs(new - scores).sum() < 1e-6:
            break
        scores = new
    top = sorted(np.argsort(scores)[::-1][:max_sentences])  # keep original order for readability
    chosen = [sentences[i] for i in top]
    return {"summary": " ".join(chosen), "sentences": chosen, "scores": [round(float(scores[i]), 4) for i in top]}


def summarize_single_complaint(text: str, category: str, entities: List[Dict[str, Any]]) -> str:
    locs = [e["text"] for e in entities if e.get("label") in ("STATION", "LANDMARK", "ROAD", "LOCATION", "WARD")]
    issues = [e["text"] for e in entities if e.get("label", "").endswith("_INCIDENT") or e.get("label") in ("WASTE_ACCUMULATION", "HEALTH_HAZARD", "ELECTRICAL_FAULT", "STRUCTURAL_RISK")]
    infra = [e["text"] for e in entities if e.get("label", "").endswith("_INFRA")]
    when = [e["text"] for e in entities if e.get("label") == "TEMPORAL"]
    parts = [category.replace("_", " ").title()]
    what = issues[0] if issues else (infra[0] if infra else None)
    if what:
        parts.append(what.lower())
    headline = ": ".join(parts[:1]) + (f" — {parts[1]}" if len(parts) > 1 else "")
    if locs:
        headline += f" at {', '.join(dict.fromkeys(locs[:2]))}"
    if when:
        headline += f" ({when[0]})"
    return headline


def _llm_abstract(instruction: str, evidence: str) -> Optional[str]:
    try:
        from backend.app.llm.providers import get_llm
        llm = get_llm()
        if not llm.available:
            return None
        return llm.complete(
            system="You are a municipal planning analyst. Summarise only facts present in the evidence. "
                   "Do not invent numbers, places or causes. Plain English, at most 3 sentences.",
            user=f"{instruction}\n\nEVIDENCE:\n{evidence}",
            max_tokens=220,
        )
    except Exception:
        return None


def summarize_complaint_cluster(records: List[Dict[str, Any]], ward_name: str, category: str,
                                use_llm: bool = True) -> Dict[str, Any]:
    total = len(records)
    cat_name = category.replace("_", " ").title()
    if total == 0:
        return {"summary": f"No {cat_name} complaints recorded in {ward_name}.", "method": "none",
                "source_record_ids": [], "key_locations": [], "cluster_count": 0, "representative_complaints": []}

    locations = Counter()
    incidents = Counter()
    for r in records:
        for e in r.get("entities") or []:
            if e.get("label") in ("STATION", "LANDMARK", "ROAD", "LOCATION"):
                locations[e["text"]] += 1
            elif e.get("label", "").endswith("_INCIDENT") or e.get("label") in ("WASTE_ACCUMULATION", "HEALTH_HAZARD"):
                incidents[e["text"].lower()] += 1
    texts = [r.get("cleaned_text") or r.get("original_text") or "" for r in records]
    extractive = textrank_summary(texts, max_sentences=3)
    top_locs = [loc for loc, _ in locations.most_common(3)]
    statuses = Counter(str(r.get("status", "OPEN")) for r in records)
    open_n = statuses.get("OPEN", 0) + statuses.get("RequestStatus.OPEN", 0)

    headline = f"{total} {cat_name} complaint{'s' if total != 1 else ''} in {ward_name}"
    if top_locs:
        headline += f", concentrated around {', '.join(f'{l} ({locations[l]})' for l in top_locs)}"
    headline += "."
    if incidents:
        headline += f" Most reported issues: {', '.join(i for i, _ in incidents.most_common(3))}."
    headline += f" {open_n} remain open."

    summary, method = headline, "extractive-textrank"
    if use_llm:
        abstract = _llm_abstract(
            f"Summarise these {total} citizen complaints about {cat_name} in {ward_name} for a planner.",
            headline + "\nRepresentative complaints:\n- " + "\n- ".join(extractive["sentences"]),
        )
        if abstract:
            summary, method = abstract.strip(), "llm-abstractive"
    return {
        "summary": summary,
        "method": method,
        "statistics": headline,
        "source_record_ids": [r.get("id") for r in records],
        "key_locations": top_locs,
        "top_issues": [i for i, _ in incidents.most_common(5)],
        "cluster_count": total,
        "representative_complaints": extractive["sentences"],
    }

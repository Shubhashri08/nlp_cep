"""Analysis of urban development reports / planning documents (PDF or plain text).

Steps: text extraction (pypdf) → section segmentation → per-section sector classification →
extractive summary (TextRank; LLM abstractive when configured) → NER → ward mention linking.
"""
import io
import re
from collections import Counter
from typing import Any, Dict, List, Tuple

from backend.app.nlp.classifier import get_classifier
from backend.app.nlp.ner import extract_entities
from backend.app.nlp.summarizer import _llm_abstract, split_sentences, textrank_summary

MAX_CHARS = 400_000
_HEADING = re.compile(r"^\s*(?:\d+(?:\.\d+)*\.?\s+)?[A-Z][A-Za-z0-9 ,&/()\-]{3,80}$")


def extract_text(filename: str, data: bytes) -> Tuple[str, int]:
    name = (filename or "").lower()
    if name.endswith(".pdf") or data[:4] == b"%PDF":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        pages = [p.extract_text() or "" for p in reader.pages]
        return "\n".join(pages)[:MAX_CHARS], len(pages)
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(enc)[:MAX_CHARS], 1
        except UnicodeDecodeError:
            continue
    return "", 0


def segment_sections(text: str, target_words: int = 220) -> List[Dict[str, str]]:
    """Splits on heading-like lines; long unstructured text is chunked by sentence count."""
    lines = [l.rstrip() for l in text.splitlines()]
    sections, title, buf = [], "Introduction", []
    for line in lines:
        stripped = line.strip()
        if stripped and len(stripped.split()) <= 10 and _HEADING.match(stripped) and not stripped.endswith("."):
            if buf:
                sections.append({"title": title, "text": " ".join(buf)})
            title, buf = stripped, []
        elif stripped:
            buf.append(stripped)
    if buf:
        sections.append({"title": title, "text": " ".join(buf)})

    out = []
    for s in sections:
        words = s["text"].split()
        if len(words) <= target_words * 2:
            out.append(s)
            continue
        sents, chunk, idx = split_sentences(s["text"]), [], 1
        for sent in sents:
            chunk.append(sent)
            if sum(len(c.split()) for c in chunk) >= target_words:
                out.append({"title": f"{s['title']} (part {idx})", "text": " ".join(chunk)})
                chunk, idx = [], idx + 1
        if chunk:
            out.append({"title": f"{s['title']} (part {idx})" if idx > 1 else s["title"], "text": " ".join(chunk)})
    return [s for s in out if len(s["text"].split()) >= 5]


def analyze_document(title: str, text: str, ward_lookup: Dict[str, Dict[str, Any]], use_llm: bool = True) -> Dict[str, Any]:
    """ward_lookup: ward_code -> {"id", "name"} for linking mentions to map features."""
    clf = get_classifier()
    sections = segment_sections(text)
    sector_counter: Counter = Counter()
    section_results = []
    for s in sections[:200]:
        primary, conf, cats = clf.predict(s["text"][:3000])
        weight = len(s["text"].split())
        sector_counter[primary] += weight
        section_results.append({
            "title": s["title"], "word_count": weight, "primary_category": primary, "confidence": conf,
            "categories": cats[:3], "summary": textrank_summary(s["text"], max_sentences=1)["summary"][:400],
        })
    total_w = sum(sector_counter.values()) or 1
    sector_distribution = [{"category": c, "share_pct": round(100 * w / total_w, 1)} for c, w in sector_counter.most_common()]

    extractive = textrank_summary(text, max_sentences=6)
    summary, method = extractive["summary"], "extractive-textrank"
    if use_llm:
        abstract = _llm_abstract(
            f"Write an executive summary of the planning document '{title}' for municipal decision makers "
            f"(key proposals, affected areas, sectors).",
            "\n".join(extractive["sentences"]) + "\n\nSector distribution: " +
            ", ".join(f"{d['category']} {d['share_pct']}%" for d in sector_distribution[:6]),
        )
        if abstract:
            summary, method = abstract.strip(), "llm-abstractive"

    entities = extract_entities(text[:60000])
    ent_counter: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for e in entities:
        key = (e["text"].lower(), e["label"])
        if key not in ent_counter:
            ent_counter[key] = {"text": e["text"], "label": e["label"], "count": 0,
                                "ward_code": e.get("ward_code"), "lat": e.get("lat"), "lng": e.get("lng")}
        ent_counter[key]["count"] += 1
    top_entities = sorted(ent_counter.values(), key=lambda x: -x["count"])[:60]

    ward_counts: Counter = Counter()
    for e in entities:
        code = e.get("ward_code")
        if code and code in ward_lookup:
            ward_counts[code] += 1
    wards_mentioned = [{"ward_code": c, "ward_id": ward_lookup[c]["id"], "ward_name": ward_lookup[c]["name"], "mentions": n}
                       for c, n in ward_counts.most_common()]

    return {
        "title": title,
        "text_length": len(text),
        "summary": summary,
        "summary_method": method,
        "key_sentences": extractive["sentences"],
        "sector_distribution": sector_distribution,
        "sections": section_results,
        "entities": top_entities,
        "wards_mentioned": wards_mentioned,
    }

import re
import unicodedata
from typing import Tuple

from backend.app.nlp.lexicon import DEVANAGARI_LEXICON, HINDI_MARKERS, HINGLISH_LEXICON, MARATHI_MARKERS

_HINGLISH_PATTERNS = [
    (re.compile(r"\b" + re.escape(term) + r"\b"), standard)
    for term, standard in sorted(HINGLISH_LEXICON.items(), key=lambda kv: -len(kv[0]))
]
_HINGLISH_TOKEN_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(t) for t in sorted(HINGLISH_LEXICON, key=len, reverse=True)) + r")\b"
)
_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")
_LATIN_WORD_RE = re.compile(r"[a-zA-Z]+")


def clean_text(text: str) -> str:
    """Normalises unicode, strips HTML, collapses repeated punctuation and whitespace."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"([!?,.:;])\1+", r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_language(text: str) -> Tuple[str, float]:
    """
    Returns (code, confidence) where code is one of:
      en    – English
      hi    – Hindi (Devanagari)
      mr    – Marathi (Devanagari)
      hi-en – Romanised Hindi/Marathi code-mixed with English ("Hinglish")
    Script ratio decides Devanagari vs Latin; whole-word lexicon matches decide code-mixing.
    """
    if not text or not text.strip():
        return "en", 0.0
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return "en", 0.0
    dev_ratio = len(_DEVANAGARI_RE.findall(text)) / len(letters)
    if dev_ratio > 0.4:
        mr = sum(1 for m in MARATHI_MARKERS if m in text)
        hi = sum(1 for m in HINDI_MARKERS if m in text)
        code = "mr" if mr > hi else "hi"
        margin = abs(mr - hi) / max(1, mr + hi)
        return code, round(min(0.99, 0.6 + 0.3 * dev_ratio + 0.1 * margin), 2)

    words = _LATIN_WORD_RE.findall(text.lower())
    if not words:
        return "en", 0.5
    hits = len(_HINGLISH_TOKEN_RE.findall(text.lower()))
    ratio = hits / len(words)
    if hits >= 2 or ratio >= 0.15:
        return "hi-en", round(min(0.95, 0.55 + ratio * 1.5), 2)
    if hits == 1:
        return "en", 0.7
    return "en", 0.95


def normalize_multilingual_text(text: str) -> str:
    """Lower-cases and appends English glosses for Hinglish / Devanagari tokens.
    Original tokens are kept so location names survive; the glosses give the classifier shared vocabulary."""
    cleaned = clean_text(text).lower()
    glosses = []
    for pattern, standard in _HINGLISH_PATTERNS:
        if pattern.search(cleaned):
            glosses.append(standard)
    for term, standard in DEVANAGARI_LEXICON.items():
        if term in cleaned:
            glosses.append(standard)
    return f"{cleaned} {' '.join(glosses)}".strip() if glosses else cleaned

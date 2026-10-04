# NLP

Pipeline (`backend/app/nlp/pipeline.py`): clean → language ID → classify → NER → geocode → embed → summarise.

| Step | Method | File |
|---|---|---|
| Language ID | Devanagari script ratio. Marathi vs Hindi by marker words. Hinglish by whole-word lexicon hits (English words were removed from the lexicon). | `cleaner.py`, `lexicon.py` |
| Normalisation | Appends English glosses for Hinglish / Devanagari tokens and keeps the originals. | `cleaner.py` |
| Classification | TF-IDF word (1–2) + char_wb (2–5) → One-vs-Rest logistic regression (C=8, balanced). Multi-label threshold 0.35. 17 categories. | `classifier.py` |
| Training data | ~2,200 generated examples (templates × phrase inventories in en / hi-en / hi / mr, 18 % multi-label). Held-out 20 % split plus a 46-sentence hand-written **gold set** never used for training. | `corpus.py` |
| NER | Longest-match OSM gazetteer (places, roads, stations, landmarks, plus aliases such as BKC and SV Road), tight ward / road / landmark patterns, domain lexicons (infrastructure, incidents, temporal, organisations). Overlaps are resolved gazetteer > pattern > lexicon, then by length. | `gazetteer.py`, `ner.py` |
| Geocoding | User GPS is never overridden. Then gazetteer, then DB cache, then Nominatim restricted to the city bounding box (`bounded=1`). Results outside the bbox are rejected. | `geocoder.py` |
| Embeddings | TF-IDF → TruncatedSVD, 64 dimensions, fitted on the corpus plus complaints. Used for semantic search. | `embeddings.py` |
| Summarisation | Per complaint: structured headline. Clusters and documents: TextRank (TF-IDF sentence graph + PageRank). LLM abstractive summary when configured, built from the extractive evidence only. | `summarizer.py` |
| Documents | pypdf text extraction → heading / length segmentation → per-section classification → summary → entity aggregation → ward linking. | `documents.py` |

Current metrics (see Model Registry): gold-set micro-F1 ≈ 0.93, primary-label accuracy 1.0. The templated held-out split scores ≈ 1.0, which only shows that templated text is easy. Report the gold-set figure. Agreement with the independent synthetic-complaint generator is ≈ 87 %.

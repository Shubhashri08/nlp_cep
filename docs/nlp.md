# Multilingual NLP Pipeline Documentation

## Pipeline Overview
The Natural Language Processing (NLP) subsystem processes citizen grievances across English, Devanagari Hindi, Marathi, and code-mixed Hinglish.

```
RAW CITIZEN TEXT
  ↓
1. Cleaning & Language Detection (English / Hindi / Marathi / Hinglish)
  ↓
2. Transliteration & Normalization (Standardizes terms like "khadde" → "potholes", "paani" → "water")
  ↓
3. Multi-Class & Multi-Label Classification (TF-IDF + OneVsRest Logistic Regression across 17 urban sectors)
  ↓
4. Named Entity Recognition (Extracts Ward, Road, Landmark, Infrastructure, Incident, and Temporal references)
  ↓
5. Location Entity Resolution (Gazetteer lookup + OpenStreetMap Nominatim with bounds checking)
  ↓
6. Dense Semantic Embedding Generation (64-D Latent Semantic vector for cosine similarity search)
  ↓
7. Automated Traceable Summarization
```

## Supported Categories
- `ROAD_INFRASTRUCTURE`
- `TRAFFIC`
- `PUBLIC_TRANSPORT`
- `WASTE_MANAGEMENT`
- `WATER_SUPPLY`
- `DRAINAGE`
- `FLOODING`
- `STREETLIGHT`
- `ELECTRICITY`
- `PUBLIC_SAFETY`
- `HEALTHCARE`
- `EDUCATION`
- `PARKS`
- `ENVIRONMENT`
- `AIR_QUALITY`
- `HOUSING`
- `OTHER`

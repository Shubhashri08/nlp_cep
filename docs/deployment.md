# Deployment & configuration

## Configuration (`.env` at the repo root; see `.env.example`)

The project `.env` takes precedence over machine-wide environment variables. Without a `.env` file, for example in a container, everything comes from environment variables. `DSS_ENV_FILE` points to an alternative file; the tests use this to avoid reading developer keys.

| Variable | Purpose |
|---|---|
| `ENV` | `prod` requires `JWT_SECRET` |
| `JWT_SECRET` | Token signing. Auto-generated and persisted in `backend/data/.jwt_secret` in dev. |
| `DEMO_MODE` | One-click role logins. **Set to false in production.** |
| `DEMO_PASSWORD` | Password for seeded demo users |
| `LLM_PROVIDER` | `gemini`, `openai` or `none` |
| `GEMINI_API_KEY`, `GEMINI_MODEL`, `GEMINI_FALLBACK_MODELS` | Default `gemini-3.5-flash`, then `gemini-3.5-flash-lite`, `gemini-2.5-flash`, `gemini-2.5-flash-lite` |
| `OPENAI_API_KEY`, `OPENAI_MODEL` | OpenAI alternative |
| `LLM_MAX_CALLS_PER_MINUTE` | Local budget (default 8) to protect free-tier quotas |
| `LLM_CACHE_TTL_SECONDS` | Assistant answer cache (default 900 s) |
| `DATABASE_URL` | Defaults to SQLite in `backend/data/` |

## Gemini free tier

Limits are **per Google Cloud project** (not per key) and are shown in the AI Studio rate-limit dashboard (https://aistudio.google.com/rate-limit). Requests-per-day quotas reset at midnight Pacific time. Exceeding a limit returns HTTP 429; an overloaded model returns 503.

The system handles both:
- It tries the next model in `GEMINI_FALLBACK_MODELS` on 404, 429 and 5xx errors.
- It enforces `LLM_MAX_CALLS_PER_MINUTE` locally. One assistant question usually costs 2–5 calls, because each tool step is a call.
- It caches identical questions.
- If all models fail, it answers with the rule-based engine and says so in the response.

Summaries, scenario narratives and recommendation briefs make one call each.

## Running in production

```bash
pip install -r requirements.txt
python -m scripts.seed --reset
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 2
cd frontend && npm ci && VITE_API_URL=https://api.example.org npm run build   # serve frontend/dist statically
```

Add the frontend origin to `BACKEND_CORS_ORIGINS`. SQLite is fine for a single municipality demo. For multi-user production, set `DATABASE_URL` to PostgreSQL (the models are SQLAlchemy 2.0; the dashboard's monthly grouping uses SQLite `strftime` and would need adapting).

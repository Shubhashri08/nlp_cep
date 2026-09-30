import os
import secrets
from typing import List
from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_ROOT = os.path.dirname(BACKEND_DIR)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.environ.get("DSS_ENV_FILE", os.path.join(REPO_ROOT, ".env")),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    PROJECT_NAME: str = "AI-Driven Urban Planning Decision Support System"
    VERSION: str = "2.0.0"
    API_V1_STR: str = "/api/v1"
    ENV: str = "dev"  # dev | prod

    # Security
    JWT_SECRET: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

    # Demo mode enables one-click role logins (never enable in production)
    DEMO_MODE: bool = True
    DEMO_PASSWORD: str = ""

    # Directories
    BASE_DIR: str = BACKEND_DIR
    DATA_DIR: str = os.path.join(BACKEND_DIR, "data")
    EXTERNAL_DATA_DIR: str = os.path.join(BACKEND_DIR, "data", "external")
    MODELS_DIR: str = os.path.join(BACKEND_DIR, "models")
    UPLOADS_DIR: str = os.path.join(BACKEND_DIR, "data", "uploads")

    # Database (SQLite by default)
    DATABASE_URL: str = f"sqlite:///{os.path.join(BACKEND_DIR, 'data', 'urban_planning.db')}"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # Study area
    CITY_NAME: str = "Mumbai"
    CITY_BBOX: List[float] = [18.85, 72.75, 19.30, 73.05]  # south, west, north, east

    # Geocoding
    NOMINATIM_ENABLED: bool = True
    NOMINATIM_USER_AGENT: str = "UrbanPlanningDSS/2.0 (academic project)"

    # LLM (openai | gemini | none)
    LLM_PROVIDER: str = "none"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"
    # Tried in order when the primary model is overloaded (503) or its quota is exhausted (429)
    GEMINI_FALLBACK_MODELS: List[str] = ["gemini-3.5-flash-lite", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
    LLM_TIMEOUT_SECONDS: float = 20.0
    # Free-tier protection: client-side cap on LLM calls per minute (each tool-calling step is one call)
    LLM_MAX_CALLS_PER_MINUTE: int = 8
    LLM_CACHE_TTL_SECONDS: int = 900

    @classmethod
    def settings_customise_sources(cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings):
        # The project's .env wins over machine-wide variables (e.g. an unrelated GEMINI_API_KEY set for another
        # project). Deployments without a .env file still configure everything through environment variables.
        return init_settings, dotenv_settings, env_settings, file_secret_settings

    @model_validator(mode="after")
    def _check_secret(self):
        if not self.JWT_SECRET:
            if self.ENV == "prod":
                raise ValueError("JWT_SECRET must be set when ENV=prod")
            # Local development: generate once and persist so --reload doesn't log everyone out
            secret_file = os.path.join(self.DATA_DIR, ".jwt_secret")
            os.makedirs(self.DATA_DIR, exist_ok=True)
            if os.path.exists(secret_file):
                with open(secret_file, encoding="utf-8") as f:
                    self.JWT_SECRET = f.read().strip()
            if not self.JWT_SECRET:
                self.JWT_SECRET = secrets.token_urlsafe(48)
                with open(secret_file, "w", encoding="utf-8") as f:
                    f.write(self.JWT_SECRET)
        return self

    @property
    def SECRET_KEY(self) -> str:
        return self.JWT_SECRET


settings = Settings()

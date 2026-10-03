"""
Central configuration. Every value comes from environment variables / backend/.env
(see .env.example at the project root). Nothing secret is hard-coded.
"""
from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]      # khetsetu/
BACKEND_DIR = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(PROJECT_ROOT / ".env"), str(BACKEND_DIR / ".env")), extra="ignore")

    # --- Runtime security ------------------------------------------------
    APP_ENV: Literal["dev", "production"] = "dev"
    REQUIRE_AUTH: bool = False
    SUPABASE_JWT_SECRET: str = ""

    # --- ML -------------------------------------------------------------
    # Folder that holds khetsetu.tflite / khetsetu.keras / class_config.json / model_meta.json
    MODEL_DIR: str = str(PROJECT_ROOT / "model")
    # Optional explicit model file (.tflite or .keras). Empty = auto-pick from MODEL_DIR.
    MODEL_PATH: str = ""
    CONFIDENCE_THRESHOLD: float = 0.70
    # auto  -> real model if model files exist, otherwise labelled demo predictions
    # true  -> always simulated (clearly labelled "Demo Mode")
    # false -> real model required; /api/predict returns 503 if it is missing
    DEMO_MODE: Literal["auto", "true", "false"] = "auto"
    # Below this share of plant-coloured pixels the photo is treated as "not a leaf"
    MIN_LEAF_RATIO: float = 0.08

    # --- Data -----------------------------------------------------------
    DATA_DIR: str = str(PROJECT_ROOT / "data")
    DATABASE_URL: str = f"sqlite:///{(BACKEND_DIR / 'khetsetu.db').as_posix()}"
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024

    # --- Web ------------------------------------------------------------
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # --- WhatsApp Cloud API (server side only) --------------------------
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = ""
    WHATSAPP_APP_SECRET: str = ""        # optional: enables X-Hub-Signature-256 checking
    WHATSAPP_GRAPH_VERSION: str = "v20.0"

    # --- Market data (data.gov.in / Agmarknet) --------------------------
    MARKET_API_KEY: str = ""
    MARKET_API_URL: str = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"
    MARKET_TIMEOUT_SECONDS: float = 8.0

    # --- Optional extras (never required) -------------------------------
    SARVAM_API_KEY: str = ""
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.8-flash"

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]


settings = Settings()

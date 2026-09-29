from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    APP_NAME: str = "FastAPI Video Audio Translation Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Gemini configuration
    GEMINI_API_KEY: str | None = None

    # Storage configuration
    UPLOAD_DIR: Path = BASE_DIR / "storage" / "uploads"
    OUTPUT_DIR: Path = BASE_DIR / "storage" / "outputs"
    MAX_UPLOAD_SIZE_MB: int = 150

    # TTS voices
    TELUGU_VOICE: str = "te-IN-MohanNeural"
    HINDI_VOICE: str = "hi-IN-MadhurNeural"

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()

# Ensure required storage directories exist
settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
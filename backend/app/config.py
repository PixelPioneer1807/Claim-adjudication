from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings and configuration"""

    # Database Configuration
    DATABASE_URL: str = "sqlite:///./claims.db"

    # AI API Configuration (OpenRouter)
    AI_BASE_URL: str = "https://openrouter.ai/api/v1"
    AI_API_KEY: str
    AI_MODEL: str = "qwen/qwen-2-vl-7b-instruct:free"

    # Application Settings
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
    ALLOWED_EXTENSIONS: set = {".jpg", ".jpeg", ".png", ".pdf"}

    # Policy Configuration
    POLICY_FILE: str = "./policy_terms.json"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

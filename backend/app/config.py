import os
from pydantic_settings import BaseSettings
from functools import lru_cache

# Resolve .env path relative to the backend directory
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ENV_FILE = os.path.join(_BACKEND_DIR, ".env")

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Gemini API
    gemini_api_key: str
    
    # Upload configuration
    upload_dir: str = os.path.join(_BACKEND_DIR, "temp_uploads")
    max_file_size: int = 52428800  # 50MB
    allowed_audio_formats: str = "mp3,wav,m4a"
    
    # Application
    app_title: str = "Retail Voice Analyst"
    debug: bool = False
    
    class Config:
        env_file = _ENV_FILE
        case_sensitive = False
    
    @property
    def allowed_formats_list(self) -> list:
        return [fmt.strip().lower() for fmt in self.allowed_audio_formats.split(",")]

@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

# Ensure upload directory exists
settings = get_settings()
os.makedirs(settings.upload_dir, exist_ok=True)

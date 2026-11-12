import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

"""BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Load environment variables: file.env first, then .env with override so .env takes precedence
if (BASE_DIR / "file.env").exists():
    load_dotenv(BASE_DIR / "file.env")
if (BASE_DIR / ".env").exists():
    load_dotenv(BASE_DIR / ".env", override=True)

class Settings(BaseSettings):
    APP_NAME: str = "AdaptiveExamEngine"
    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/data/exam_engine.db"
    DEBUG: bool = True
    GEMINI_API_KEY: str = ""

    # Supabase Credentials (supports both Next.js and standard Python conventions)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    NEXT_PUBLIC_SUPABASE_URL: str = ""
    NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY: str = ""
    NEXT_PUBLIC_SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""

    @property
    def effective_supabase_url(self) -> str:
        return (
            self.SUPABASE_URL
            or self.NEXT_PUBLIC_SUPABASE_URL
            or os.getenv("SUPABASE_URL", "")
            or os.getenv("NEXT_PUBLIC_SUPABASE_URL", "")
        ).strip()

    @property
    def effective_supabase_key(self) -> str:
        return (
            self.SUPABASE_SERVICE_ROLE_KEY
            or self.SUPABASE_KEY
            or self.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
            or self.NEXT_PUBLIC_SUPABASE_ANON_KEY
            or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
            or os.getenv("SUPABASE_KEY", "")
            or os.getenv("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY", "")
            or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY", "")
        ).strip()

    @property
    def is_supabase_configured(self) -> bool:
        return bool(self.effective_supabase_url and self.effective_supabase_key)

    class Config:
        env_file = (str(BASE_DIR / ".env"), str(BASE_DIR / "file.env"))
        extra = "ignore"

settings = Settings()"""

from pydantic_settings import BaseSettings
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

class Settings(BaseSettings):
    APP_NAME: str = "AdaptiveExamEngine"
    DATABASE_URL: str
    DEBUG: bool = True
    GEMINI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

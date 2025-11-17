"""
Configuration management for the FastAPI backend
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class Settings:
    """Application settings"""

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./video_generator.db")

    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = int(os.getenv("REDIS_MAX_CONNECTIONS", "50"))
    REDIS_SOCKET_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_TIMEOUT", "5"))
    REDIS_SOCKET_CONNECT_TIMEOUT: int = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))
    REDIS_RETRY_ON_TIMEOUT: bool = os.getenv("REDIS_RETRY_ON_TIMEOUT", "true").lower() == "true"
    REDIS_HEALTH_CHECK_INTERVAL: int = int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", "30"))

    # CORS
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "http://localhost:3000")

    # Application
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

    # API Keys
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    REPLICATE_API_KEY: str = os.getenv("REPLICATE_API_KEY", "")
    REPLICATE_API_TOKEN: str = os.getenv("REPLICATE_API_TOKEN", "")  # Alternative naming
    ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Music Video Module
    MV_DEBUG_MODE: bool = os.getenv("MV_DEBUG_MODE", "false").lower() == "true"
    MOCK_VID_GENS: bool = os.getenv("MOCK_VID_GENS", "false").lower() == "true"

    # ElevenLabs settings
    # Default voice: Sarah - Clear, professional, neutral tone
    # Alternative voices available through ElevenLabs API
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

    # Replicate Configuration
    REPLICATE_MAX_RETRIES: int = int(os.getenv("REPLICATE_MAX_RETRIES", "3"))
    REPLICATE_TIMEOUT: int = int(os.getenv("REPLICATE_TIMEOUT", "600"))

    # Cloud Storage Configuration
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "firebase")  # Options: "firebase" or "s3"
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "")
    
    # Firebase Storage (Google Cloud Storage)
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    PRESIGNED_URL_EXPIRY: int = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))  # 1 hour in seconds
    
    # Video Serving Configuration
    SERVE_FROM_CLOUD: bool = os.getenv("SERVE_FROM_CLOUD", "false").lower() == "true"  # Serve videos from cloud storage
    
    # Asset Retention Policy
    KEEP_INTERMEDIATE_ASSETS: bool = os.getenv("KEEP_INTERMEDIATE_ASSETS", "true").lower() == "true"
    ASSET_BACKUP_LIMIT: int = int(os.getenv("ASSET_BACKUP_LIMIT", "1"))  # Keep 1 previous version

    # Job Queue
    JOB_QUEUE_NAME: str = "video_generation_queue"
    JOB_STATUS_CHANNEL: str = "job_status_updates"
    JOB_PROGRESS_CHANNEL: str = "job_progress_updates"

    # Job timeouts (in seconds)
    JOB_TIMEOUT: int = int(os.getenv("JOB_TIMEOUT", "3600"))  # 1 hour
    JOB_RESULT_TTL: int = int(os.getenv("JOB_RESULT_TTL", "86400"))  # 24 hours

    @property
    def cors_origins_list(self) -> list:
        """Parse CORS origins into a list"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]


# Global settings instance
settings = Settings()

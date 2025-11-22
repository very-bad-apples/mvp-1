"""
Configuration management for the FastAPI backend
"""

import os
from typing import Optional
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

    # Mock video generation delay configuration (in seconds)
    MOCK_VIDEO_DELAY_MIN: float = float(os.getenv("MOCK_VIDEO_DELAY_MIN", "5.0"))
    MOCK_VIDEO_DELAY_MAX: float = float(os.getenv("MOCK_VIDEO_DELAY_MAX", "10.0"))

    # ElevenLabs settings
    # Default voice: Sarah - Clear, professional, neutral tone
    # Alternative voices available through ElevenLabs API
    ELEVENLABS_VOICE_ID: str = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

    # Replicate Configuration
    REPLICATE_MAX_RETRIES: int = int(os.getenv("REPLICATE_MAX_RETRIES", "3"))
    REPLICATE_TIMEOUT: int = int(os.getenv("REPLICATE_TIMEOUT", "600"))

    # Cloud Storage Configuration
    # Default to S3 for new MV pipeline; Firebase still supported for legacy endpoints
    STORAGE_BACKEND: str = os.getenv("STORAGE_BACKEND", "s3")  # Options: "firebase" or "s3"
    STORAGE_BUCKET: str = os.getenv("STORAGE_BUCKET", "")
    
    # Firebase Storage (Google Cloud Storage)
    FIREBASE_CREDENTIALS_PATH: str = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    
    # AWS S3 Configuration
    AWS_ACCESS_KEY_ID: str = os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY: str = os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    PRESIGNED_URL_EXPIRY: int = int(os.getenv("PRESIGNED_URL_EXPIRY", "3600"))  # 1 hour in seconds
    
    # DynamoDB Configuration
    DYNAMODB_ENDPOINT: str = os.getenv("DYNAMODB_ENDPOINT", "http://localhost:8001")
    DYNAMODB_REGION: str = os.getenv("DYNAMODB_REGION", "us-east-1")
    DYNAMODB_TABLE_NAME: str = os.getenv("DYNAMODB_TABLE_NAME", "MVProjects")
    # Use local DynamoDB for development
    USE_LOCAL_DYNAMODB: bool = os.getenv("USE_LOCAL_DYNAMODB", "true").lower() == "true"
    
    @property
    def dynamodb_access_key_id(self) -> str:
        """Get DynamoDB access key, using fake credentials for local dev if not set."""
        if self.USE_LOCAL_DYNAMODB:
            # Local development: use fake credentials if not provided
            return self.AWS_ACCESS_KEY_ID if self.AWS_ACCESS_KEY_ID else "fakeAccessKey"
        # Production: return actual credentials (validation happens at startup)
        return self.AWS_ACCESS_KEY_ID
    
    @property
    def dynamodb_secret_access_key(self) -> str:
        """Get DynamoDB secret key, using fake credentials for local dev if not set."""
        if self.USE_LOCAL_DYNAMODB:
            # Local development: use fake credentials if not provided
            return self.AWS_SECRET_ACCESS_KEY if self.AWS_SECRET_ACCESS_KEY else "fakeSecretKey"
        # Production: return actual credentials (validation happens at startup)
        return self.AWS_SECRET_ACCESS_KEY
    
    def validate_dynamodb_config(self) -> None:
        """
        Validate DynamoDB configuration at startup.
        Raises ValueError if production mode lacks required credentials.
        """
        if not self.USE_LOCAL_DYNAMODB:
            if not self.AWS_ACCESS_KEY_ID:
                raise ValueError("AWS_ACCESS_KEY_ID is required when USE_LOCAL_DYNAMODB=false")
            if not self.AWS_SECRET_ACCESS_KEY:
                raise ValueError("AWS_SECRET_ACCESS_KEY is required when USE_LOCAL_DYNAMODB=false")
    
    # Video Serving Configuration
    SERVE_FROM_CLOUD: bool = os.getenv("SERVE_FROM_CLOUD", "false").lower() == "true"  # Serve videos from cloud storage
    
    # Asset Retention Policy
    KEEP_INTERMEDIATE_ASSETS: bool = os.getenv("KEEP_INTERMEDIATE_ASSETS", "true").lower() == "true"
    ASSET_BACKUP_LIMIT: int = int(os.getenv("ASSET_BACKUP_LIMIT", "1"))  # Keep 1 previous version

    # FFmpeg Configuration (for audio processing)
    FFMPEG_PATH: Optional[str] = os.getenv("FFMPEG_PATH", None)  # Optional path to ffmpeg executable
    
    # YouTube Download Configuration (for yt-dlp)
    # Use cookies to bypass YouTube bot detection
    # Options for YTDLP_COOKIES_FROM_BROWSER: "chrome", "firefox", "edge", "safari", "opera", "brave"
    # If set, yt-dlp will automatically extract cookies from the specified browser
    YTDLP_COOKIES_FROM_BROWSER: Optional[str] = os.getenv("YTDLP_COOKIES_FROM_BROWSER", None)
    # Alternative: Path to a cookies file (Netscape format or JSON)
    # Can be exported using: yt-dlp --cookies-from-browser chrome --cookies cookies.txt
    YTDLP_COOKIES_FILE: Optional[str] = os.getenv("YTDLP_COOKIES_FILE", None)

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

"""
Core Configuration - Phase 1
Load settings from environment variables
"""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings"""
    
    # App Config
    APP_NAME: str = "Crashbot"
    VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Security
    SECRET_KEY: str = "change-this-in-production"
    API_KEY_SALT: str = "change-this-salt"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3002", "http://localhost:8002"]
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://crashbot:crashbot_password@localhost:5435/crashbot_db"
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = "redis://localhost:6381/0"
    REDIS_CACHE_TTL: int = 3600
    
    # Storage
    STORAGE_TYPE: str = "local"  # local, s3, gcs, azure
    DUMP_STORAGE_PATH: str = "./storage/dumps"
    MAX_DUMP_SIZE_MB: int = 500
    DUMP_RETENTION_DAYS: int = 30
    
    # AWS S3 (optional)
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = ""
    
    # LLM Config (Phase 2)
    # Siemens AI API (Primary)
    SIEMENS_API_KEY: str = ""
    
    # Backup API Keys
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    
    # LLM Provider Configuration
    LLM_PROVIDER: str = "siemens"  # siemens, openai, anthropic
    LLM_BASE_URL: str = "https://api.siemens.com/llm/v1"
    LLM_MODEL: str = "qwen3-30b-a3b-instruct-2507"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.3
    LLM_TIMEOUT_SECONDS: int = 60
    LLM_MAX_RETRIES: int = 3
    
    # Fallback Configuration
    FALLBACK_PROVIDER: str = "openai"
    FALLBACK_MODEL: str = "gpt-4o-mini"
    
    # Vector DB (Phase 1.5)
    VECTOR_DB_TYPE: str = "chroma"
    CHROMA_PATH: str = "./storage/chroma_db"
    PINECONE_API_KEY: str = ""
    PINECONE_ENVIRONMENT: str = ""
    
    # Embeddings Configuration
    EMBEDDING_PROVIDER: str = "siemens"  # siemens, openai
    EMBEDDING_BASE_URL: str = "https://api.siemens.com/llm/v1"
    EMBEDDING_MODEL: str = "qwen3-embedding-8b"
    EMBEDDING_DIMENSIONS: int = 4096  # 4096 for 8b, 1024 for 0.6b
    
    # Reranking Configuration
    ENABLE_RERANKING: bool = True
    RERANKER_MODEL: str = "qwen3-reranker-8b"
    RERANKING_INITIAL_LIMIT: int = 20
    RERANKING_FINAL_LIMIT: int = 5
    
    # Search
    BING_SEARCH_API_KEY: str = ""
    GOOGLE_SEARCH_API_KEY: str = ""
    
    # Debugger
    WINDBG_PATH: str = r"C:\Program Files (x86)\Windows Kits\10\Debuggers\x64\cdb.exe"
    GDB_PATH: str = "/usr/bin/gdb"  # Linux debugger
    LLDB_PATH: str = "/usr/bin/lldb"  # macOS debugger
    DEBUGGER_TIMEOUT_SECONDS: int = 120
    MAX_STACK_DEPTH: int = 50
    
    # Symbol Server
    MICROSOFT_SYMBOL_SERVER: str = "https://msdl.microsoft.com/download/symbols"
    SYMBOL_CACHE_PATH: str = "./storage/symbols"
    SYMBOL_TIMEOUT_SECONDS: int = 30
    
    # Worker Config (Phase 4)
    CELERY_BROKER_URL: str = "redis://localhost:6381/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6381/2"
    WORKER_CONCURRENCY: int = 4
    
    # Monitoring
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: str = ""
    ENABLE_METRICS: bool = True
    PROMETHEUS_PORT: int = 9090
    
    # Email (Phase 5)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@crashbot.dev"
    
    # Slack (Phase 5)
    SLACK_WEBHOOK_URL: str = ""
    SLACK_NOTIFICATIONS_ENABLED: bool = False

    # JIRA (Phase 5)
    JIRA_URL: str = ""
    JIRA_API_TOKEN: str = ""
    JIRA_PROJECT_KEY: str = "CRASH"

    # GitHub (Phase 5)
    GITHUB_TOKEN: str = ""
    GITHUB_REPO: str = ""
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_PERIOD_SECONDS: int = 60
    
    # Feature Flags (Phase 5)
    ENABLE_BATCH_ANALYSIS: bool = True
    ENABLE_CHAT_FOLLOWUP: bool = True
    ENABLE_CODE_INTEGRATION: bool = True
    ENABLE_ML_CLASSIFICATION: bool = True
    ENABLE_CRASH_CLUSTERING: bool = True
    MIN_CLUSTER_SIZE: int = 3
    CLUSTERING_SIMILARITY_THRESHOLD: float = 0.7
    
    # Advanced LLM Features
    ENABLE_FUNCTION_CALLING: bool = True
    ENABLE_MULTI_MODEL_ENSEMBLE: bool = False
    ENSEMBLE_MODELS: str = "qwen3-30b-a3b-instruct-2507,devstral-small-2505,mistral-7b-instruct"
    ENSEMBLE_MIN_CONSENSUS: int = 2
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()


# Ensure storage directories exist
def ensure_directories():
    """Create necessary directories"""
    os.makedirs(settings.DUMP_STORAGE_PATH, exist_ok=True)
    os.makedirs(settings.SYMBOL_CACHE_PATH, exist_ok=True)
    os.makedirs(settings.CHROMA_PATH, exist_ok=True)
    os.makedirs("./storage", exist_ok=True)
    os.makedirs("./logs", exist_ok=True)


ensure_directories()

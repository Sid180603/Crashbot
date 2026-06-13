"""
Logging Configuration - Phase 1
Structured logging with JSON format for production
"""
import logging
import sys
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from app.core.config import settings


class StructuredFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "crash_id"):
            log_data["crash_id"] = record.crash_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        if hasattr(record, "cost"):
            log_data["cost"] = record.cost
        
        return json.dumps(log_data)


def setup_logging():
    """Configure logging for the application"""
    
    # Create logs directory
    log_dir = Path("./logs")
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging format (JSON for file, human-readable for console)
    console_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Set log level
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Console handler (human-readable)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(logging.Formatter(console_format))
    
    # File handler (structured JSON)
    file_handler = logging.FileHandler(log_dir / "crashbot.log")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(StructuredFormatter())
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        handlers=[console_handler, file_handler]
    )
    
    # Set library log levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured - Level: {settings.LOG_LEVEL}")


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)


def log_with_context(logger: logging.Logger, level: str, message: str, **context):
    """
    Log with additional context fields
    
    Example:
        log_with_context(logger, "info", "Analysis started", 
                        crash_id="123", user_id="456", duration=1.5)
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra=context)

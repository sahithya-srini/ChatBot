# File: app/config/logging_config.py

from enum import Enum
from typing import Dict

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

# Default logging configuration
DEFAULT_LOG_LEVEL = LogLevel.INFO

# Service-specific logging settings
SERVICE_LOG_LEVELS: Dict[str, str] = {
    # Add other services as needed
}

# You can also have environment-specific configurations
DEVELOPMENT_LOG_LEVELS: Dict[str, str] = {
    "app": LogLevel.DEBUG,
    "app.services": LogLevel.DEBUG,
    "uvicorn": LogLevel.INFO,
    "fastapi": LogLevel.DEBUG,
}

PRODUCTION_LOG_LEVELS: Dict[str, str] = {
    "app": LogLevel.INFO,
    "app.services": LogLevel.INFO,
    "uvicorn": LogLevel.WARNING,
    "fastapi": LogLevel.WARNING,
}
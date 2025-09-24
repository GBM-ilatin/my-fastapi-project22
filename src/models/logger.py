```python
# logger.py
import logging
import sys
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from sqlmodel import SQLModel, Field
from pydantic import BaseModel, validator
import json


class LogLevel(str, Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogEntry(SQLModel, table=True):
    """Database model for storing log entries."""
    
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow, index=True)
    level: LogLevel = Field(index=True)
    message: str = Field(max_length=1000)
    module: Optional[str] = Field(default=None, max_length=100)
    function: Optional[str] = Field(default=None, max_length=100)
    line_number: Optional[int] = Field(default=None)
    extra_data: Optional[str] = Field(default=None)  # JSON string for additional data
    
    class Config:
        """Pydantic configuration."""
        use_enum_values = True


class LogEntryCreate(BaseModel):
    """Model for creating log entries."""
    
    level: LogLevel
    message: str = Field(max_length=1000)
    module: Optional[str] = Field(default=None, max_length=100)
    function: Optional[str] = Field(default=None, max_length=100)
    line_number: Optional[int] = Field(default=None, ge=1)
    extra_data: Optional[Dict[str, Any]] = Field(default=None)
    
    @validator('message')
    def validate_message(cls, v):
        """Validate message is not empty."""
        if not v or not v.strip():
            raise ValueError('Message cannot be empty')
        return v.strip()


class LogEntryResponse(BaseModel):
    """Model for log entry responses."""
    
    id: int
    timestamp: datetime
    level: LogLevel
    message: str
    module: Optional[str]
    function: Optional[str]
    line_number: Optional[int]
    extra_data: Optional[Dict[str, Any]]
    
    class Config:
        """Pydantic configuration."""
        from_attributes = True


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line_number': record.lineno,
            'pathname': record.pathname,
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data['extra_data'] = record.extra_data
            
        return json.dumps(log_data, default=str)


class Logger:
    """Structured logging component."""
    
    def __init__(self, name: str = "app", level: LogLevel = LogLevel.INFO):
        """
        Initialize logger.
        
        Args:
            name: Logger name
            level: Logging level
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value))
        
        # Remove existing handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # Add console handler with structured formatter
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(console_handler)
        
        # Prevent propagation to root logger
        self.logger.propagate = False
    
    def _log(self, level: LogLevel, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """
        Internal logging method.
        
        Args:
            level: Log level
            message: Log message
            extra_data: Additional data to include
        """
        extra = {'extra_data': extra_data} if extra_data else {}
        self.logger.log(getattr(logging, level.value), message, extra=extra)
    
    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log debug message."""
        self._log(LogLevel.DEBUG, message, extra_data)
    
    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log info message."""
        self._log(LogLevel.INFO, message, extra_data)
    
    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log warning message."""
        self._log(LogLevel.WARNING, message, extra_data)
    
    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log error message."""
        self._log(LogLevel.ERROR, message, extra_data)
    
    def critical(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log critical message."""
        self._log(LogLevel.CRITICAL, message, extra_data)
    
    def exception(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """Log exception with traceback."""
        extra = {'extra_data': extra_data} if extra_data else {}
        self.logger.exception(message, extra=extra)


# config.py
from pydantic import BaseSettings, Field
from typing import Optional


class LoggingConfig(BaseSettings):
    """Configuration for logging component."""
    
    log_level: LogLevel = Field(default=LogLevel.INFO, description="Default logging level")
    log_format: str = Field(default="structured", description="Log format (structured or simple)")
    log_file_path: Optional[str] = Field(default=None, description="Path to log file")
    log_file_max_size: int = Field(default=10485760, description="Max log file size in bytes (10MB)")
    log_file_backup_count: int = Field(default=5, description="Number of backup log files")
    enable_database_logging: bool = Field(default=False, description="Enable database logging")
    
    class Config:
        """Pydantic configuration."""
        env_prefix = "LOG_"
        case_sensitive = False


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    app_name: str = Field(default="FastAPI App", description="Application name")
    debug: bool = Field(default=False, description="Debug mode")
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    class Config:
        """Pydantic configuration."""
        env_nested_delimiter = "__"
        case_sensitive = False
```
```python
# logger.py
import logging
import logging.config
import json
import sys
from datetime import datetime
from typing import Any, Dict, Optional, Union
from pathlib import Path
from abc import ABC, abstractmethod

class LogFormatter(logging.Formatter):
    """Custom formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
            
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry, ensure_ascii=False)

class LoggerServiceInterface(ABC):
    """Interface for logger service."""
    
    @abstractmethod
    def debug(self, message: str, **kwargs: Any) -> None:
        pass
    
    @abstractmethod
    def info(self, message: str, **kwargs: Any) -> None:
        pass
    
    @abstractmethod
    def warning(self, message: str, **kwargs: Any) -> None:
        pass
    
    @abstractmethod
    def error(self, message: str, **kwargs: Any) -> None:
        pass
    
    @abstractmethod
    def critical(self, message: str, **kwargs: Any) -> None:
        pass

class LoggerService(LoggerServiceInterface):
    """Service for structured logging functionality."""
    
    def __init__(self, name: str = "app", config: Optional[Dict[str, Any]] = None):
        """
        Initialize logger service.
        
        Args:
            name: Logger name
            config: Logger configuration
        """
        self.name = name
        self.config = config or {}
        self._logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup and configure structured logger."""
        logger = logging.getLogger(self.name)
        
        if logger.handlers:
            return logger
            
        logger.setLevel(self.config.get("level", logging.INFO))
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(LogFormatter())
        logger.addHandler(console_handler)
        
        # File handler if configured
        if log_file := self.config.get("file_path"):
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(LogFormatter())
            logger.addHandler(file_handler)
        
        logger.propagate = False
        return logger
    
    def _log_with_extra(self, level: int, message: str, **kwargs: Any) -> None:
        """Log message with extra data."""
        extra_data = {k: v for k, v in kwargs.items() if v is not None}
        self._logger.log(level, message, extra={"extra_data": extra_data})
    
    def debug(self, message: str, **kwargs: Any) -> None:
        """Log debug message."""
        self._log_with_extra(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs: Any) -> None:
        """Log info message."""
        self._log_with_extra(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs: Any) -> None:
        """Log warning message."""
        self._log_with_extra(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs: Any) -> None:
        """Log error message."""
        self._log_with_extra(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs: Any) -> None:
        """Log critical message."""
        self._log_with_extra(logging.CRITICAL, message, **kwargs)
    
    def log_request(self, method: str, path: str, status_code: int, 
                   duration: float, **kwargs: Any) -> None:
        """Log HTTP request."""
        self.info(
            f"{method} {path} - {status_code}",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration * 1000, 2),
            **kwargs
        )
    
    def log_exception(self, message: str, exception: Exception, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._logger.exception(
            message,
            extra={"extra_data": {**kwargs, "exception_type": type(exception).__name__}}
        )

class LoggerFactory:
    """Factory for creating logger instances."""
    
    _instances: Dict[str, LoggerService] = {}
    
    @classmethod
    def create_logger(cls, name: str, config: Optional[Dict[str, Any]] = None) -> LoggerService:
        """
        Create or get existing logger instance.
        
        Args:
            name: Logger name
            config: Logger configuration
            
        Returns:
            LoggerService instance
        """
        if name not in cls._instances:
            cls._instances[name] = LoggerService(name, config)
        return cls._instances[name]
    
    @classmethod
    def get_logger(cls, name: str) -> Optional[LoggerService]:
        """Get existing logger instance."""
        return cls._instances.get(name)

# config.py
import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

class LoggerConfig:
    """Configuration for logger service."""
    
    def __init__(self):
        self.level = self._get_log_level()
        self.file_path = self._get_log_file_path()
        self.max_file_size = int(os.getenv("LOG_MAX_FILE_SIZE", "10485760"))  # 10MB
        self.backup_count = int(os.getenv("LOG_BACKUP_COUNT", "5"))
        self.format_json = os.getenv("LOG_FORMAT_JSON", "true").lower() == "true"
    
    def _get_log_level(self) -> int:
        """Get log level from environment."""
        level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        return getattr(logging, level_str, logging.INFO)
    
    def _get_log_file_path(self) -> Optional[str]:
        """Get log file path from environment."""
        if log_file := os.getenv("LOG_FILE_PATH"):
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            return str(log_path)
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "level": self.level,
            "file_path": self.file_path,
            "max_file_size": self.max_file_size,
            "backup_count": self.backup_count,
            "format_json": self.format_json,
        }

class LoggerConfigService:
    """Service for managing logger configuration."""
    
    def __init__(self):
        self._config = LoggerConfig()
    
    def get_config(self) -> Dict[str, Any]:
        """Get logger configuration."""
        return self._config.to_dict()
    
    def update_config(self, **kwargs: Any) -> None:
        """Update logger configuration."""
        for key, value in kwargs.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
    
    def create_logger_service(self, name: str = "app") -> LoggerService:
        """Create logger service with current configuration."""
        return LoggerFactory.create_logger(name, self.get_config())

# Dependency injection
def get_logger_config_service() -> LoggerConfigService:
    """Dependency injection for logger config service."""
    return LoggerConfigService()

def get_logger_service(
    name: str = "app",
    config_service: LoggerConfigService = None
) -> LoggerService:
    """Dependency injection for logger service."""
    if config_service is None:
        config_service = get_logger_config_service()
    return config_service.create_logger_service(name)
```
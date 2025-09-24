```python
# logger.py
import logging
import json
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum
from pathlib import Path

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class StructuredFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'extra_data'):
            log_entry.update(record.extra_data)
            
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_entry)

class StructuredLogger:
    def __init__(self, name: str, level: str = "INFO", log_file: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))
        
        # Clear existing handlers
        self.logger.handlers.clear()
        
        formatter = StructuredFormatter()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def log(self, level: str, message: str, extra_data: Optional[Dict[str, Any]] = None):
        log_level = getattr(logging, level.upper())
        extra = {"extra_data": extra_data} if extra_data else {}
        self.logger.log(log_level, message, extra=extra)
    
    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        self.log("DEBUG", message, extra_data)
    
    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        self.log("INFO", message, extra_data)
    
    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        self.log("WARNING", message, extra_data)
    
    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        self.log("ERROR", message, extra_data)
    
    def critical(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        self.log("CRITICAL", message, extra_data)

# config.py
from pydantic import BaseSettings
from typing import Optional

class LoggerConfig(BaseSettings):
    log_level: str = "INFO"
    log_file: Optional[str] = None
    app_name: str = "fastapi-app"
    
    class Config:
        env_prefix = "LOGGER_"

# models.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class LogEntryCreate(BaseModel):
    level: LogLevel = Field(..., description="Log level")
    message: str = Field(..., min_length=1, max_length=1000, description="Log message")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional log data")

class LogEntryResponse(BaseModel):
    id: str = Field(..., description="Log entry ID")
    timestamp: datetime = Field(..., description="Log timestamp")
    level: LogLevel = Field(..., description="Log level")
    message: str = Field(..., description="Log message")
    logger_name: str = Field(..., description="Logger name")
    extra_data: Optional[Dict[str, Any]] = Field(None, description="Additional log data")

class LoggerConfigResponse(BaseModel):
    logger_name: str = Field(..., description="Logger name")
    log_level: LogLevel = Field(..., description="Current log level")
    log_file: Optional[str] = Field(None, description="Log file path")
    handlers_count: int = Field(..., description="Number of handlers")

class LoggerConfigUpdate(BaseModel):
    log_level: Optional[LogLevel] = Field(None, description="New log level")
    log_file: Optional[str] = Field(None, description="New log file path")

class LogQueryParams(BaseModel):
    level: Optional[LogLevel] = Field(None, description="Filter by log level")
    start_time: Optional[datetime] = Field(None, description="Start time filter")
    end_time: Optional[datetime] = Field(None, description="End time filter")
    limit: int = Field(100, ge=1, le=1000, description="Number of entries to return")
    offset: int = Field(0, ge=0, description="Number of entries to skip")

# services.py
import uuid
from typing import List, Optional
from datetime import datetime
import json
from pathlib import Path

class LoggerService:
    def __init__(self, config: LoggerConfig):
        self.config = config
        self.logger = StructuredLogger(
            name=config.app_name,
            level=config.log_level,
            log_file=config.log_file
        )
        self.log_entries = []  # In-memory storage for demo
    
    def create_log_entry(self, log_data: LogEntryCreate) -> LogEntryResponse:
        entry_id = str(uuid.uuid4())
        timestamp = datetime.utcnow()
        
        # Log the entry
        self.logger.log(log_data.level.value, log_data.message, log_data.extra_data)
        
        # Store for retrieval (in production, this would be in a database)
        log_entry = LogEntryResponse(
            id=entry_id,
            timestamp=timestamp,
            level=log_data.level,
            message=log_data.message,
            logger_name=self.config.app_name,
            extra_data=log_data.extra_data
        )
        self.log_entries.append(log_entry)
        
        return log_entry
    
    def get_log_entries(self, query_params: LogQueryParams) -> List[LogEntryResponse]:
        filtered_entries = self.log_entries
        
        if query_params.level:
            filtered_entries = [e for e in filtered_entries if e.level == query_params.level]
        
        if query_params.start_time:
            filtered_entries = [e for e in filtered_entries if e.timestamp >= query_params.start_time]
        
        if query_params.end_time:
            filtered_entries = [e for e in filtered_entries if e.timestamp <= query_params.end_time]
        
        # Apply pagination
        start_idx = query_params.offset
        end_idx = start_idx + query_params.limit
        
        return filtered_entries[start_idx:end_idx]
    
    def get_log_entry(self, entry_id: str) -> Optional[LogEntryResponse]:
        return next((entry for entry in self.log_entries if entry.id == entry_id), None)
    
    def get_logger_config(self) -> LoggerConfigResponse:
        return LoggerConfigResponse(
            logger_name=self.config.app_name,
            log_level=LogLevel(self.config.log_level),
            log_file=self.config.log_file,
            handlers_count=len(self.logger.logger.handlers)
        )
    
    def update_logger_config(self, config_update: LoggerConfigUpdate) -> LoggerConfigResponse:
        if config_update.log_level:
            self.config.log_level = config_update.log_level.value
            self.logger.logger.setLevel(getattr(logging, config_update.log_level.value))
        
        if config_update.log_file is not None:
            self.config.log_file = config_update.log_file
            # Recreate logger with new file
            self.logger = StructuredLogger(
                name=self.config.app_name,
                level=self.config.log_level,
                log_file=self.config.log_file
            )
        
        return self.get_logger_config()
    
    def delete_log_entries(self) -> int:
        count = len(self.log_entries)
        self.log_entries.clear()
        return count

# dependencies.py
from functools import lru_cache

@lru_cache()
def get_logger_config() -> LoggerConfig:
    return LoggerConfig()

def get_logger_service(config: LoggerConfig = Depends(get_logger_config)) -> LoggerService:
    return LoggerService(config)

# router.py
from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import List, Optional

router = APIRouter(prefix="/logger", tags=["Logger"])

@router.post(
    "/logs",
    response_model=LogEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create log entry",
    description="Create a new log entry with specified level and message"
)
async def create_log_entry(
    log_data: LogEntryCreate,
    service: LoggerService = Depends(get_logger_service)
) -> LogEntryResponse:
    try:
        return service.create_log_entry(log_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create log entry: {str(e)}"
        )

@router.get(
    "/logs",
    response_model=List[LogEntryResponse],
    summary="Get log entries",
    description="Retrieve log entries with optional filtering and pagination"
)
async def get_log_entries(
    level: Optional[LogLevel] = Query(None, description="Filter by log level"),
    start_time: Optional[datetime] = Query(None, description="Start time filter"),
    end_time: Optional[datetime] = Query(None, description="End time filter"),
    limit: int = Query(100, ge=1, le=1000, description="Number of entries to return"),
    offset: int = Query(0, ge=0, description="Number of entries to skip"),
    service: LoggerService = Depends(get_logger_service)
) -> List[LogEntryResponse]:
    try:
        query_params = LogQueryParams(
            level=level,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset
        )
        return service.get_log_entries(query_params)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve log entries: {str(e)}"
        )

@router.get(
    "/logs/{entry_id}",
    response_model=LogEntryResponse,
    summary="Get log entry by ID",
    description="Retrieve a specific log entry by its ID"
)
async def get_log_entry(
    entry_id: str,
    service: LoggerService = Depends(get_logger_service)
) -> LogEntryResponse:
    log_entry = service.get_log_entry(entry_id)
    if not log_entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Log entry with ID {entry_id} not found"
        )
    return log_entry

@router.get(
    "/config",
    response_model=LoggerConfigResponse,
    summary="Get logger configuration",
    description="Retrieve current logger configuration"
)
async def get_logger_config(
    service: LoggerService = Depends(get_logger_service)
) -> LoggerConfigResponse:
    try:
        return service.get_logger_config()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve logger configuration: {str(e)}"
        )

@router.put(
    "/config",
    response_model=LoggerConfigResponse,
    summary="Update logger configuration",
    description="Update logger configuration settings"
)
async def update_logger_config(
    config_update: LoggerConfigUpdate,
    service: LoggerService = Depends(get_logger_service)
) -> LoggerConfigResponse:
    try:
        return service.update_logger_config(config_update)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update logger configuration: {str(e)}"
        )

@router.delete(
    "/logs",
    summary="Delete all log entries",
    description="Delete all stored log entries"
)
async def delete_log_entries(
    service: LoggerService = Depends(get_logger_service)
) -> dict:
    try:
        count = service.delete_log_entries()
        return {"message": f"Deleted {count} log entries"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete log entries: {str(e)}"
        )

@router.post(
    "/logs/debug",
    response_model=LogEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create debug log entry",
    description="Convenience endpoint for creating debug log entries"
)
async def create_debug_log(
    message: str,
    extra_data: Optional[Dict[str, Any]] = None,
    service: LoggerService = Depends(get_logger_service)
) -> LogEntryResponse:
    log_data = LogEntryCreate(level=LogLevel.DEBUG, message=message, extra_data=extra_data)
    return await create_log_entry(log_data, service)

@router.post(
    "/logs/info",
    response_model=LogEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create info log entry",
    description="Convenience endpoint for creating info log entries"
)
async def create_info_log(
    message: str,
    extra_data: Optional[Dict[str, Any]] = None,
    service: LoggerService = Depends(get_logger_service)
) -> LogEntryResponse:
    log_data = LogEntryCreate(level=LogLevel.INFO, message=message, extra_data=extra_data)
    return await create_log_entry(log_data, service)

@router.post(
    "/logs/warning",
    response_model=LogEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create warning log entry",
    description="Convenience endpoint for creating warning log entries"
)
async def create_warning_log(
    message: str,
    extra_data: Optional[Dict[str, Any]] = None,
    service: LoggerService = Depends(get_logger_service)
) -> LogEntryResponse:
    log_data = LogEntryCreate(level=LogLevel.WARNING, message=message, extra_data=extra_data)
    return await create_log_entry(log_data, service)

@router.post(
    "/logs/error",
    response_model=LogEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary
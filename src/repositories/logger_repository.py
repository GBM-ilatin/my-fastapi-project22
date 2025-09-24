```python
# logger.py
import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from sqlmodel import SQLModel, Field, Session, select, create_engine
from sqlalchemy.exc import SQLAlchemyError
from abc import ABC, abstractmethod

class LogLevel(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class LogEntry(SQLModel, table=True):
    __tablename__ = "log_entries"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    level: LogLevel
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    extra_data: Optional[str] = None  # JSON string for additional data
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None

class LogEntryCreate(SQLModel):
    level: LogLevel
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None

class LogEntryUpdate(SQLModel):
    level: Optional[LogLevel] = None
    message: Optional[str] = None
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None

class LogRepositoryInterface(ABC):
    @abstractmethod
    def create(self, log_entry: LogEntryCreate) -> LogEntry:
        pass
    
    @abstractmethod
    def get_by_id(self, log_id: int) -> Optional[LogEntry]:
        pass
    
    @abstractmethod
    def get_all(self, skip: int = 0, limit: int = 100) -> List[LogEntry]:
        pass
    
    @abstractmethod
    def get_by_level(self, level: LogLevel, skip: int = 0, limit: int = 100) -> List[LogEntry]:
        pass
    
    @abstractmethod
    def update(self, log_id: int, log_update: LogEntryUpdate) -> Optional[LogEntry]:
        pass
    
    @abstractmethod
    def delete(self, log_id: int) -> bool:
        pass

class LogRepository(LogRepositoryInterface):
    def __init__(self, session: Session):
        self.session = session
    
    def create(self, log_entry: LogEntryCreate) -> LogEntry:
        """Create a new log entry in the database."""
        try:
            extra_data_json = None
            if log_entry.extra_data:
                extra_data_json = json.dumps(log_entry.extra_data)
            
            db_log = LogEntry(
                level=log_entry.level,
                message=log_entry.message,
                module=log_entry.module,
                function=log_entry.function,
                line_number=log_entry.line_number,
                extra_data=extra_data_json
            )
            
            self.session.add(db_log)
            self.session.commit()
            self.session.refresh(db_log)
            return db_log
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Failed to create log entry: {str(e)}")
    
    def get_by_id(self, log_id: int) -> Optional[LogEntry]:
        """Retrieve a log entry by its ID."""
        try:
            statement = select(LogEntry).where(LogEntry.id == log_id)
            return self.session.exec(statement).first()
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to retrieve log entry {log_id}: {str(e)}")
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[LogEntry]:
        """Retrieve all log entries with pagination."""
        try:
            statement = select(LogEntry).offset(skip).limit(limit).order_by(LogEntry.timestamp.desc())
            return list(self.session.exec(statement).all())
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to retrieve log entries: {str(e)}")
    
    def get_by_level(self, level: LogLevel, skip: int = 0, limit: int = 100) -> List[LogEntry]:
        """Retrieve log entries by log level."""
        try:
            statement = (
                select(LogEntry)
                .where(LogEntry.level == level)
                .offset(skip)
                .limit(limit)
                .order_by(LogEntry.timestamp.desc())
            )
            return list(self.session.exec(statement).all())
        except SQLAlchemyError as e:
            raise RuntimeError(f"Failed to retrieve log entries by level {level}: {str(e)}")
    
    def update(self, log_id: int, log_update: LogEntryUpdate) -> Optional[LogEntry]:
        """Update an existing log entry."""
        try:
            db_log = self.get_by_id(log_id)
            if not db_log:
                return None
            
            update_data = log_update.dict(exclude_unset=True)
            
            if "extra_data" in update_data and update_data["extra_data"]:
                update_data["extra_data"] = json.dumps(update_data["extra_data"])
            
            for field, value in update_data.items():
                setattr(db_log, field, value)
            
            db_log.updated_at = datetime.utcnow()
            
            self.session.add(db_log)
            self.session.commit()
            self.session.refresh(db_log)
            return db_log
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Failed to update log entry {log_id}: {str(e)}")
    
    def delete(self, log_id: int) -> bool:
        """Delete a log entry by its ID."""
        try:
            db_log = self.get_by_id(log_id)
            if not db_log:
                return False
            
            self.session.delete(db_log)
            self.session.commit()
            return True
        except SQLAlchemyError as e:
            self.session.rollback()
            raise RuntimeError(f"Failed to delete log entry {log_id}: {str(e)}")

class StructuredLogger:
    def __init__(self, name: str, log_repository: LogRepositoryInterface):
        self.logger = logging.getLogger(name)
        self.log_repository = log_repository
        self._configure_logger()
    
    def _configure_logger(self) -> None:
        """Configure the Python logger with structured formatting."""
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.DEBUG)
    
    def _log_to_db(self, level: LogLevel, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log message to database through repository."""
        try:
            import inspect
            frame = inspect.currentframe().f_back.f_back
            
            log_entry = LogEntryCreate(
                level=level,
                message=message,
                module=frame.f_globals.get('__name__'),
                function=frame.f_code.co_name,
                line_number=frame.f_lineno,
                extra_data=extra_data
            )
            
            self.log_repository.create(log_entry)
        except Exception as e:
            # Don't let logging errors break the application
            self.logger.error(f"Failed to log to database: {str(e)}")
    
    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log debug message."""
        self.logger.debug(message, extra=extra_data or {})
        self._log_to_db(LogLevel.DEBUG, message, extra_data)
    
    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log info message."""
        self.logger.info(message, extra=extra_data or {})
        self._log_to_db(LogLevel.INFO, message, extra_data)
    
    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log warning message."""
        self.logger.warning(message, extra=extra_data or {})
        self._log_to_db(LogLevel.WARNING, message, extra_data)
    
    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log error message."""
        self.logger.error(message, extra=extra_data or {})
        self._log_to_db(LogLevel.ERROR, message, extra_data)
    
    def critical(self, message: str, extra_data: Optional[Dict[str, Any]] = None) -> None:
        """Log critical message."""
        self.logger.critical(message, extra=extra_data or {})
        self._log_to_db(LogLevel.CRITICAL, message, extra_data)

class LoggerService:
    def __init__(self, log_repository: LogRepositoryInterface):
        self.log_repository = log_repository
    
    def get_logger(self, name: str) -> StructuredLogger:
        """Get a structured logger instance."""
        return StructuredLogger(name, self.log_repository)
    
    def get_logs(self, skip: int = 0, limit: int = 100) -> List[LogEntry]:
        """Retrieve logs through repository."""
        return self.log_repository.get_all(skip, limit)
    
    def get_logs_by_level(self, level: LogLevel, skip: int = 0, limit: int = 100) -> List[LogEntry]:
        """Retrieve logs by level through repository."""
        return self.log_repository.get_by_level(level, skip, limit)
    
    def delete_log(self, log_id: int) -> bool:
        """Delete a log entry through repository."""
        return self.log_repository.delete(log_id)
```

```python
# config.py
import os
from typing import Optional
from sqlmodel import create_engine, Session, SQLModel
from logger import LogRepository, LoggerService, LogEntry

class DatabaseConfig:
    def __init__(
        self,
        database_url: Optional[str] = None,
        echo: bool = False
    ):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", 
            "sqlite:///./logs.db"
        )
        self.echo = echo

class LoggerConfig:
    def __init__(self, database_config: DatabaseConfig):
        self.database_config = database_config
        self.engine = create_engine(
            database_config.database_url,
            echo=database_config.echo
        )
        self._create_tables()
    
    def _create_tables(self) -> None:
        """Create database tables."""
        SQLModel.metadata.create_all(self.engine)
    
    def get_session(self) -> Session:
        """Get database session."""
        return Session(self.engine)
    
    def get_log_repository(self, session: Session) -> LogRepository:
        """Get log repository instance."""
        return LogRepository(session)
    
    def get_logger_service(self, session: Session) -> LoggerService:
        """Get logger service instance."""
        log_repository = self.get_log_repository(session)
        return LoggerService(log_repository)

# Dependency injection setup
def create_logger_dependencies(database_url: Optional[str] = None) -> tuple[Session, LoggerService]:
    """Create logger dependencies for dependency injection."""
    db_config = DatabaseConfig(database_url)
    logger_config = LoggerConfig(db_config)
    session = logger_config.get_session()
    logger_service = logger_config.get_logger_service(session)
    return session, logger_service

# Example usage factory
def get_application_logger(name: str = "app", database_url: Optional[str] = None):
    """Factory function to get application logger."""
    session, logger_service = create_logger_dependencies(database_url)
    return logger_service.get_logger(name)
```
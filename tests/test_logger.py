```python
import pytest
import logging
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from io import StringIO


class Logger:
    """Structured logging component using Python logging library."""
    
    def __init__(self, name: str, level: str = "INFO", format_type: str = "json"):
        self.name = name
        self.level = getattr(logging, level.upper())
        self.format_type = format_type
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)
        self._setup_formatter()
    
    def _setup_formatter(self):
        """Setup the log formatter based on format type."""
        if self.format_type == "json":
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        for handler in self.logger.handlers:
            handler.setFormatter(formatter)
    
    def add_console_handler(self):
        """Add console handler to logger."""
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.level)
        self._setup_handler_formatter(console_handler)
        self.logger.addHandler(console_handler)
    
    def add_file_handler(self, filepath: str):
        """Add file handler to logger."""
        file_handler = logging.FileHandler(filepath)
        file_handler.setLevel(self.level)
        self._setup_handler_formatter(file_handler)
        self.logger.addHandler(file_handler)
    
    def _setup_handler_formatter(self, handler):
        """Setup formatter for a specific handler."""
        if self.format_type == "json":
            formatter = logging.Formatter(
                '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}'
            )
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        handler.setFormatter(formatter)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log(logging.CRITICAL, message, **kwargs)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal logging method with structured data."""
        if kwargs:
            structured_message = f"{message} | {json.dumps(kwargs)}"
        else:
            structured_message = message
        self.logger.log(level, structured_message)
    
    def set_level(self, level: str):
        """Set logging level."""
        self.level = getattr(logging, level.upper())
        self.logger.setLevel(self.level)
        for handler in self.logger.handlers:
            handler.setLevel(self.level)
    
    def clear_handlers(self):
        """Clear all handlers from logger."""
        self.logger.handlers.clear()


@pytest.fixture
def logger_instance():
    """Create a Logger instance for testing."""
    logger = Logger("test_logger", "DEBUG", "json")
    yield logger
    # Cleanup
    logger.clear_handlers()
    logging.getLogger("test_logger").handlers.clear()


@pytest.fixture
def temp_log_file():
    """Create a temporary log file for testing."""
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
        temp_file = f.name
    yield temp_file
    # Cleanup
    if os.path.exists(temp_file):
        os.unlink(temp_file)


class TestLoggerInitialization:
    """Test Logger initialization and setup."""
    
    def test_logger_init_default_params(self):
        """Test Logger initialization with default parameters."""
        logger = Logger("test_app")
        
        assert logger.name == "test_app"
        assert logger.level == logging.INFO
        assert logger.format_type == "json"
        assert logger.logger.name == "test_app"
        assert logger.logger.level == logging.INFO
    
    def test_logger_init_custom_params(self):
        """Test Logger initialization with custom parameters."""
        logger = Logger("custom_app", "ERROR", "text")
        
        assert logger.name == "custom_app"
        assert logger.level == logging.ERROR
        assert logger.format_type == "text"
        assert logger.logger.name == "custom_app"
        assert logger.logger.level == logging.ERROR
    
    def test_logger_init_invalid_level(self):
        """Test Logger initialization with invalid log level."""
        with pytest.raises(AttributeError):
            Logger("test_app", "INVALID_LEVEL")


class TestLoggerHandlers:
    """Test Logger handler management."""
    
    def test_add_console_handler(self, logger_instance):
        """Test adding console handler to logger."""
        initial_handler_count = len(logger_instance.logger.handlers)
        
        logger_instance.add_console_handler()
        
        assert len(logger_instance.logger.handlers) == initial_handler_count + 1
        assert isinstance(logger_instance.logger.handlers[-1], logging.StreamHandler)
    
    def test_add_file_handler(self, logger_instance, temp_log_file):
        """Test adding file handler to logger."""
        initial_handler_count = len(logger_instance.logger.handlers)
        
        logger_instance.add_file_handler(temp_log_file)
        
        assert len(logger_instance.logger.handlers) == initial_handler_count + 1
        assert isinstance(logger_instance.logger.handlers[-1], logging.FileHandler)
    
    def test_clear_handlers(self, logger_instance):
        """Test clearing all handlers from logger."""
        logger_instance.add_console_handler()
        logger_instance.add_console_handler()
        
        assert len(logger_instance.logger.handlers) > 0
        
        logger_instance.clear_handlers()
        
        assert len(logger_instance.logger.handlers) == 0
    
    @patch('logging.StreamHandler')
    def test_setup_handler_formatter_json(self, mock_stream_handler, logger_instance):
        """Test handler formatter setup for JSON format."""
        mock_handler = Mock()
        mock_stream_handler.return_value = mock_handler
        
        logger_instance.add_console_handler()
        
        mock_handler.setFormatter.assert_called_once()
        formatter_call = mock_handler.setFormatter.call_args[0][0]
        assert '"timestamp"' in formatter_call._fmt
        assert '"level"' in formatter_call._fmt
    
    @patch('logging.StreamHandler')
    def test_setup_handler_formatter_text(self, mock_stream_handler):
        """Test handler formatter setup for text format."""
        logger = Logger("test_logger", "INFO", "text")
        mock_handler = Mock()
        mock_stream_handler.return_value = mock_handler
        
        logger.add_console_handler()
        
        mock_handler.setFormatter.assert_called_once()
        formatter_call = mock_handler.setFormatter.call_args[0][0]
        assert '%(asctime)s - %(name)s - %(levelname)s - %(message)s' == formatter_call._fmt


class TestLoggerLevels:
    """Test Logger level management."""
    
    def test_set_level_valid(self, logger_instance):
        """Test setting valid log level."""
        logger_instance.set_level("ERROR")
        
        assert logger_instance.level == logging.ERROR
        assert logger_instance.logger.level == logging.ERROR
    
    def test_set_level_invalid(self, logger_instance):
        """Test setting invalid log level."""
        with pytest.raises(AttributeError):
            logger_instance.set_level("INVALID")
    
    def test_set_level_updates_handlers(self, logger_instance):
        """Test that setting level updates all handlers."""
        logger_instance.add_console_handler()
        handler = logger_instance.logger.handlers[0]
        
        logger_instance.set_level("CRITICAL")
        
        assert handler.level == logging.CRITICAL


class TestLoggerMethods:
    """Test Logger logging methods."""
    
    @patch('logging.Logger.log')
    def test_debug_method(self, mock_log, logger_instance):
        """Test debug logging method."""
        logger_instance.debug("Debug message")
        
        mock_log.assert_called_once_with(logging.DEBUG, "Debug message")
    
    @patch('logging.Logger.log')
    def test_info_method(self, mock_log, logger_instance):
        """Test info logging method."""
        logger_instance.info("Info message")
        
        mock_log.assert_called_once_with(logging.INFO, "Info message")
    
    @patch('logging.Logger.log')
    def test_warning_method(self, mock_log, logger_instance):
        """Test warning logging method."""
        logger_instance.warning("Warning message")
        
        mock_log.assert_called_once_with(logging.WARNING, "Warning message")
    
    @patch('logging.Logger.log')
    def test_error_method(self, mock_log, logger_instance):
        """Test error logging method."""
        logger_instance.error("Error message")
        
        mock_log.assert_called_once_with(logging.ERROR, "Error message")
    
    @patch('logging.Logger.log')
    def test_critical_method(self, mock_log, logger_instance):
        """Test critical logging method."""
        logger_instance.critical("Critical message")
        
        mock_log.assert_called_once_with(logging.CRITICAL, "Critical message")
    
    @patch('logging.Logger.log')
    def test_log_with_kwargs(self, mock_log, logger_instance):
        """Test logging with structured data kwargs."""
        logger_instance.info("Test message", user_id=123, action="login")
        
        expected_message = 'Test message | {"user_id": 123, "action": "login"}'
        mock_log.assert_called_once_with(logging.INFO, expected_message)
    
    @patch('logging.Logger.log')
    def test_log_without_kwargs(self, mock_log, logger_instance):
        """Test logging without structured data kwargs."""
        logger_instance.info("Simple message")
        
        mock_log.assert_called_once_with(logging.INFO, "Simple message")


class TestLoggerIntegration:
    """Test Logger integration scenarios."""
    
    def test_file_logging_integration(self, logger_instance, temp_log_file):
        """Test complete file logging integration."""
        logger_instance.add_file_handler(temp_log_file)
        
        logger_instance.info("Test log message", request_id="12345")
        
        with open(temp_log_file, 'r') as f:
            log_content = f.read()
        
        assert "Test log message" in log_content
        assert "request_id" in log_content
        assert "12345" in log_content
    
    def test_multiple_handlers_integration(self, logger_instance, temp_log_file):
        """Test logging with multiple handlers."""
        logger_instance.add_console_handler()
        logger_instance.add_file_handler(temp_log_file)
        
        assert len(logger_instance.logger.handlers) == 2
        
        logger_instance.error("Multi-handler test")
        
        with open(temp_log_file, 'r') as f:
            log_content = f.read()
        
        assert "Multi-handler test" in log_content
    
    def test_level_filtering_integration(self, logger_instance, temp_log_file):
        """Test log level filtering integration."""
        logger_instance.set_level("ERROR")
        logger_instance.add_file_handler(temp_log_file)
        
        logger_instance.debug("Debug message")  # Should not appear
        logger_instance.info("Info message")    # Should not appear
        logger_instance.error("Error message")  # Should appear
        
        with open(temp_log_file, 'r') as f:
            log_content = f.read()
        
        assert "Debug message" not in log_content
        assert "Info message" not in log_content
        assert "Error message" in log_content


class TestLoggerEdgeCases:
    """Test Logger edge cases and error conditions."""
    
    def test_empty_message_logging(self, logger_instance):
        """Test logging empty message."""
        with patch('logging.Logger.log') as mock_log:
            logger_instance.info("")
            mock_log.assert_called_once_with(logging.INFO, "")
    
    def test_none_message_logging(self, logger_instance):
        """Test logging None message."""
        with patch('logging.Logger.log') as mock_log:
            logger_instance.info(None)
            mock_log.assert_called_once_with(logging.INFO, "None")
    
    def test_complex_kwargs_serialization(self, logger_instance):
        """Test logging with complex kwargs that need JSON serialization."""
        with patch('logging.Logger.log') as mock_log:
            complex_data = {
                "nested": {"key": "value"},
                "list": [1, 2, 3],
                "bool": True
            }
            logger_instance.info("Complex data", **complex_data)
            
            call_args = mock_log.call_args[0]
            assert "Complex data |" in call_args[1]
            assert "nested" in call_args[1]
    
    def test_logger_name_uniqueness(self):
        """Test that loggers with same name share the same underlying logger."""
        logger1 = Logger("same_name")
        logger2 = Logger("same_name")
        
        assert logger1.logger is logger2.logger
    
    def test_handler_level_inheritance(self, logger_instance):
        """Test that new handlers inherit logger level."""
        logger_instance.set_level("CRITICAL")
        logger_instance.add_console_handler()
        
        handler = logger_instance.logger.handlers[-1]
        assert handler.level == logging.CRITICAL
```
import logging
import logging.handlers
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, Optional

from config import config


class SecurityFilter(logging.Filter):
    """Filter to remove sensitive data from logs"""

    SENSITIVE_KEYS = {
        "password",
        "token",
        "key",
        "secret",
        "api_key",
        "access_token",
        "refresh_token",
        "authorization",
        "auth",
        "credential",
        "private",
    }

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter sensitive information from log records"""
        if hasattr(record, "msg") and isinstance(record.msg, str):
            # Check for sensitive data in message
            msg_lower = record.msg.lower()
            for sensitive in self.SENSITIVE_KEYS:
                if sensitive in msg_lower:
                    # Replace with redacted version
                    record.msg = self._redact_sensitive_data(record.msg)
                    break

        # Also check args if present
        if hasattr(record, "args") and record.args:
            record.args = tuple(self._redact_if_sensitive(arg) for arg in record.args)

        return True

    def _redact_sensitive_data(self, text: str) -> str:
        """Redact sensitive data from text"""
        import re

        # Redact patterns that look like tokens/keys
        patterns = [
            r'(token["\s]*[:=]["\s]*)([^"\s]{8,})(["\s])',
            r'(key["\s]*[:=]["\s]*)([^"\s]{8,})(["\s])',
            r'(secret["\s]*[:=]["\s]*)([^"\s]{8,})(["\s])',
            r'(password["\s]*[:=]["\s]*)([^"\s]{4,})(["\s])',
        ]

        for pattern in patterns:
            text = re.sub(pattern, r"\1[REDACTED]\3", text, flags=re.IGNORECASE)

        return text

    def _redact_if_sensitive(self, value: Any) -> Any:
        """Redact value if it looks sensitive"""
        if isinstance(value, str) and len(value) > 8:
            value_lower = value.lower()
            for sensitive in self.SENSITIVE_KEYS:
                if sensitive in value_lower:
                    return "[REDACTED]"
        return value


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[1;31m",  # Bold Red
        "RESET": "\033[0m",  # Reset
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format record with colors for console"""
        if not sys.stderr.isatty():
            # Not a TTY, don't use colors
            return super().format(record)

        # Add color to levelname
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
            )

        formatted = super().format(record)

        # Reset levelname for next use
        record.levelname = levelname

        return formatted


class StructuredFormatter(logging.Formatter):
    """Structured JSON formatter for production logs"""

    def format(self, record: logging.LogRecord) -> str:
        """Format record as JSON"""
        import json
        from datetime import datetime

        # Build structured log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "traceback": "".join(traceback.format_exception(*record.exc_info)),
            }

        # Add extra fields if present
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in {
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "getMessage",
                }:
                    log_entry["extra"] = log_entry.get("extra", {})
                    log_entry["extra"][key] = value

        try:
            return json.dumps(log_entry, default=str, ensure_ascii=False)
        except (TypeError, ValueError):
            # Fallback to simple format if JSON serialization fails
            return super().format(record)


def setup_logging(app=None) -> logging.Logger:
    """Configure comprehensive logging for the application"""

    # Create logs directory
    log_dir = Path(config.UPLOAD_FOLDER) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    # Clear any existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    # Set root logger level
    root_logger.setLevel(config.get_log_level())

    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(config.get_log_level())

    if config.is_production():
        # Production: structured JSON logs
        console_formatter = StructuredFormatter()
    else:
        # Development: colored, readable logs
        console_formatter = ColoredFormatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%H:%M:%S",
        )

    console_handler.setFormatter(console_formatter)
    console_handler.addFilter(SecurityFilter())
    root_logger.addHandler(console_handler)

    # File handler for persistent logs
    if not config.is_testing():
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.INFO)

        file_formatter = StructuredFormatter()
        file_handler.setFormatter(file_formatter)
        file_handler.addFilter(SecurityFilter())
        root_logger.addHandler(file_handler)

        # Error file handler for errors only
        error_handler = logging.handlers.RotatingFileHandler(
            log_dir / "error.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding="utf-8",
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        error_handler.addFilter(SecurityFilter())
        root_logger.addHandler(error_handler)

    # Configure specific loggers

    # Flask request logging
    werkzeug_logger = logging.getLogger("werkzeug")
    if config.is_production():
        werkzeug_logger.setLevel(logging.WARNING)
    else:
        werkzeug_logger.setLevel(logging.INFO)

    # SQLAlchemy logging
    sqlalchemy_logger = logging.getLogger("sqlalchemy.engine")
    if config.DEBUG and not config.is_testing():
        sqlalchemy_logger.setLevel(logging.INFO)
    else:
        sqlalchemy_logger.setLevel(logging.WARNING)

    # Application logger
    app_logger = logging.getLogger("missioncontrol")
    app_logger.setLevel(config.get_log_level())

    # Configure Flask app logging if provided
    if app:
        app.logger = app_logger

        # Disable Flask's default handler to avoid duplicates
        if app.logger.handlers:
            app.logger.handlers.clear()

        app.logger.propagate = True

    # Log startup message
    logger = logging.getLogger("missioncontrol.startup")
    logger.info(
        f"Logging configured - Environment: {config.ENVIRONMENT}, "
        f"Level: {config.LOG_LEVEL}, Production: {config.is_production()}"
    )

    return app_logger


def log_comprehensive_error(
    error_type: str,
    error_message: str,
    error_location: str,
    error_data: Optional[Dict[str, Any]] = None,
    exc_info: Optional[tuple] = None,
) -> None:
    """
    Log comprehensive error information

    Args:
        error_type: Type/category of error
        error_message: Error message
        error_location: Location where error occurred
        error_data: Additional error context data
        exc_info: Exception info tuple from sys.exc_info()
    """
    logger = logging.getLogger("missioncontrol.errors")

    # Build error context
    error_context = {
        "error_type": error_type,
        "location": error_location,
        "error_data": error_data or {},
        "python_version": sys.version,
        "platform": sys.platform,
        "pid": os.getpid(),
    }

    # Log with extra context
    logger.error(
        f"[{error_type}] {error_message} (Location: {error_location})",
        extra=error_context,
        exc_info=exc_info,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the given name"""
    return logging.getLogger(f"missioncontrol.{name}")


# Performance monitoring helpers
class PerformanceLogger:
    """Context manager for logging performance metrics"""

    def __init__(self, operation_name: str, logger_name: str = "performance"):
        self.operation_name = operation_name
        self.logger = get_logger(logger_name)
        self.start_time = None

    def __enter__(self):
        import time

        self.start_time = time.time()
        self.logger.debug(f"Starting operation: {self.operation_name}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        import time

        duration = time.time() - self.start_time

        if exc_type:
            self.logger.warning(
                f"Operation failed: {self.operation_name} "
                f"(Duration: {duration:.3f}s, Error: {exc_type.__name__})"
            )
        else:
            level = logging.WARNING if duration > 1.0 else logging.DEBUG
            self.logger.log(
                level,
                f"Operation completed: {self.operation_name} "
                f"(Duration: {duration:.3f}s)",
            )


# Security event logging
def log_security_event(
    event_type: str,
    details: Dict[str, Any],
    severity: str = "INFO",
    user_id: Optional[int] = None,
) -> None:
    """Log security-related events"""
    from flask import has_request_context, request

    logger = get_logger("security")

    # Build security context
    security_context = {
        "event_type": event_type,
        "severity": severity.upper(),
        "user_id": user_id,
        "details": details,
    }

    # Add request context if available
    if has_request_context():
        security_context.update(
            {
                "ip_address": request.environ.get("REMOTE_ADDR", "unknown"),
                "user_agent": request.headers.get("User-Agent", "unknown"),
                "endpoint": request.endpoint,
                "method": request.method,
                "url": request.url,
            }
        )

    # Log with appropriate level
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }

    log_level = level_map.get(severity.upper(), logging.INFO)

    logger.log(log_level, f"Security event: {event_type}", extra=security_context)


# Initialize logger for this module
logger = get_logger("config")

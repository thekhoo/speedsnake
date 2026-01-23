import json
import logging
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

import speedtest.environment as env

LOG_MAX_BYTES = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 10


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(level: int = logging.INFO) -> None:
    """Configure logging with JSON format and rotating file handler."""
    log_dir = env.get_log_dir()
    log_dir.mkdir(parents=True, exist_ok=True)

    log_file = log_dir / "speedtest.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # File handler with rotation
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
    )
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    # Console handler for visibility
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
    root_logger.addHandler(console_handler)

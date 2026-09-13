import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any


class JSONFormatter(logging.Formatter):
    def __init__(self, service_name: str = "forum-service"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.service_name,
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Bổ sung các trường structured tracing nếu có
        for attr in ("request_id", "method", "path", "status_code", "duration_ms"):
            if hasattr(record, attr):
                log_entry[attr] = getattr(record, attr)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


def setup_logging(service_name: str = "forum-service", log_level: int = logging.INFO) -> None:
    """
    Cấu hình logging định dạng JSON structured cho toàn bộ service.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Xoá các handler mặc định cũ để tránh duplicate log
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter(service_name=service_name))
    root_logger.addHandler(handler)

    # Đồng bộ format log cho uvicorn
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        u_logger = logging.getLogger(logger_name)
        u_logger.handlers = [handler]
        u_logger.propagate = False

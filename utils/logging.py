import json
import logging
from datetime import datetime, timezone


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "event"):
            payload["event"] = record.event

        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id

        if hasattr(record, "user_id"):
            payload["user_id"] = record.user_id

        if hasattr(record, "path"):
            payload["path"] = record.path

        if hasattr(record, "method"):
            payload["method"] = record.method

        if hasattr(record, "status_code"):
            payload["status_code"] = record.status_code

        if hasattr(record, "duration_ms"):
            payload["duration_ms"] = record.duration_ms

        if hasattr(record, "city"):
            payload["city"] = record.city

        if hasattr(record, "radius"):
            payload["radius"] = record.radius

        if hasattr(record, "from_cache"):
            payload["from_cache"] = record.from_cache

        if hasattr(record, "result_count"):
            payload["result_count"] = record.result_count

        if hasattr(record, "quota_allowed"):
            payload["quota_allowed"] = record.quota_allowed

        if hasattr(record, "is_authenticated"):
            payload["is_authenticated"] = record.is_authenticated

        if hasattr(record, "client_ip"):
            payload["client_ip"] = record.client_ip

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False)
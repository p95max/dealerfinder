import logging
import time

from utils.http import _get_client_ip

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        started_at = time.monotonic()
        response = self.get_response(request)
        duration_ms = round((time.monotonic() - started_at) * 1000, 2)

        logger.info(
            "HTTP request finished",
            extra={
                "event": "http_request_finished",
                "user_id": request.user.pk if getattr(request, "user",
                                                      None) and request.user.is_authenticated else None,
                "is_authenticated": bool(getattr(request, "user", None) and request.user.is_authenticated),
                "path": request.path,
                "method": request.method,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": _get_client_ip(request),
            },
        )
        return response
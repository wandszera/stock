"""Structured logging, request correlation, and application metrics."""

import contextvars
import json
import logging
import re
import sys
import time
import uuid
from datetime import datetime, timezone

from fastapi import Request
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware


request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="-"
)
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

HTTP_REQUESTS = Counter(
    "stock_http_requests_total",
    "Total de requisicoes HTTP processadas.",
    ("method", "route", "status"),
)
HTTP_DURATION = Histogram(
    "stock_http_request_duration_seconds",
    "Duracao das requisicoes HTTP em segundos.",
    ("method", "route"),
)
HTTP_IN_PROGRESS = Gauge(
    "stock_http_requests_in_progress",
    "Requisicoes HTTP atualmente em processamento.",
    ("method",),
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_context.get(),
        }
        event_data = getattr(record, "event_data", None)
        if event_data:
            payload.update(event_data)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str) -> logging.Logger:
    logger = logging.getLogger("stock")
    logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(level.upper())
    logger.propagate = False
    return logger


def normalize_request_id(value: str | None) -> str:
    if value and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return str(uuid.uuid4())


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, logger: logging.Logger):
        super().__init__(app)
        self.logger = logger

    async def dispatch(self, request: Request, call_next):
        request_id = normalize_request_id(request.headers.get("X-Request-ID"))
        token = request_id_context.set(request_id)
        started_at = time.perf_counter()
        method = request.method
        status_code = 500
        HTTP_IN_PROGRESS.labels(method=method).inc()

        try:
            try:
                response = await call_next(request)
                status_code = response.status_code
            except SQLAlchemyError:
                status_code = 503
                self.logger.exception(
                    "database_request_failed",
                    extra={"event_data": {"event": "database_error", "method": method}},
                )
                response = JSONResponse(
                    status_code=status_code,
                    content={"detail": "database_unavailable", "request_id": request_id},
                )
            except Exception:
                self.logger.exception(
                    "unhandled_request_error",
                    extra={"event_data": {"event": "unhandled_error", "method": method}},
                )
                response = JSONResponse(
                    status_code=status_code,
                    content={"detail": "internal_server_error", "request_id": request_id},
                )

            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration = time.perf_counter() - started_at
            route = getattr(request.scope.get("route"), "path", None) or "unmatched"
            HTTP_REQUESTS.labels(method=method, route=route, status=str(status_code)).inc()
            HTTP_DURATION.labels(method=method, route=route).observe(duration)
            HTTP_IN_PROGRESS.labels(method=method).dec()
            self.logger.info(
                "http_request_completed",
                extra={
                    "event_data": {
                        "event": "http_request",
                        "method": method,
                        "route": route,
                        "status": status_code,
                        "duration_ms": round(duration * 1000, 2),
                    }
                },
            )
            request_id_context.reset(token)

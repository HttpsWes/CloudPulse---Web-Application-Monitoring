"""Local sample application for the first phase of CloudPulse AI."""

import json
import logging
import os
import time
import uuid
from collections import deque
from datetime import datetime, timezone
from threading import Lock

from flask import Flask, g, jsonify, render_template, request


class JsonFormatter(logging.Formatter):
    """One JSON object per log line, ready for later CloudWatch collection."""

    def format(self, record):
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
        }
        if hasattr(record, "fields"):
            entry.update(record.fields)
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry)


def create_app():
    app = Flask(__name__)
    app.config["START_TIME"] = time.monotonic()
    app.config["ENABLE_DEMO_ERRORS"] = os.getenv("ENABLE_DEMO_ERRORS") == "1"
    measurements = {"requests": 0, "http_5xx": 0, "latencies_ms": deque(maxlen=100), "last_5xx_at": None}
    measurements_lock = Lock()

    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False

    @app.before_request
    def start_request():
        g.started_at = time.monotonic()
        g.request_id = uuid.uuid4().hex

    @app.after_request
    def log_request(response):
        duration_ms = round((time.monotonic() - g.started_at) * 1000, 2)
        with measurements_lock:
            measurements["requests"] += 1
            measurements["latencies_ms"].append(duration_ms)
            if response.status_code >= 500:
                measurements["http_5xx"] += 1
                measurements["last_5xx_at"] = datetime.now(timezone.utc).isoformat()
        response.headers["X-Request-ID"] = g.request_id
        app.logger.info(
            "request_complete",
            extra={"fields": {
                "request_id": g.request_id,
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }},
        )
        return response

    @app.get("/")
    def home():
        return render_template("index.html")

    @app.get("/api/health")
    def health():
        # A 200 response proves this Flask process answered; it is not a full health verdict.
        return jsonify(service="cloudpulse-ai", check="process_responding")

    @app.get("/api/status")
    def status():
        with measurements_lock:
            latencies = measurements["latencies_ms"]
            observed = {
                "requests_since_start": measurements["requests"],
                "http_5xx_since_start": measurements["http_5xx"],
                "avg_response_ms_last_100": round(sum(latencies) / len(latencies), 2) if latencies else None,
                "last_5xx_at": measurements["last_5xx_at"],
            }
        return jsonify(
            service="cloudpulse-ai",
            process_uptime_seconds=round(time.monotonic() - app.config["START_TIME"], 1),
            checked_at=datetime.now(timezone.utc).isoformat(),
            **observed,
        )

    @app.get("/api/demo/error")
    def demo_error():
        # Opt in explicitly; never expose a deliberate failure on a deployed app.
        if not app.config["ENABLE_DEMO_ERRORS"] or request.remote_addr not in (
            "127.0.0.1", "::1"
        ):
            return jsonify(error="not_found"), 404
        try:
            raise RuntimeError("Controlled demo failure")
        except RuntimeError:
            app.logger.exception(
                "demo_error",
                extra={"fields": {"request_id": g.request_id, "path": request.path}},
            )
            return jsonify(error="demo_failure", request_id=g.request_id), 500

    return app


app = create_app()

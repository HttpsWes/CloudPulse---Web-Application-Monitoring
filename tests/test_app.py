import json
import unittest
from unittest.mock import patch

from app import create_app


class AppTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_health_and_status(self):
        health = self.client.get("/api/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json["status"], "healthy")
        self.assertIn("X-Request-ID", health.headers)

        status = self.client.get("/api/status")
        self.assertEqual(status.status_code, 200)
        self.assertGreaterEqual(status.json["uptime_seconds"], 0)

    def test_error_route_is_disabled_by_default(self):
        self.assertEqual(self.client.get("/api/demo/error").status_code, 404)

    def test_error_route_logs_and_returns_500_when_locally_enabled(self):
        self.app.config["ENABLE_DEMO_ERRORS"] = True
        with patch.object(self.app.logger, "exception") as log:
            response = self.client.get("/api/demo/error")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json["request_id"], response.headers["X-Request-ID"])
        log.assert_called_once()
        self.assertEqual(
            self.client.get("/api/demo/error", environ_base={"REMOTE_ADDR": "203.0.113.2"}).status_code,
            404,
        )

    def test_json_formatter_has_monitoring_fields(self):
        from app import JsonFormatter
        import logging

        record = logging.LogRecord("test", logging.INFO, "", 0, "request_complete", (), None)
        record.fields = {"status_code": 200, "duration_ms": 2.5}
        line = json.loads(JsonFormatter().format(record))
        self.assertEqual(line["status_code"], 200)
        self.assertEqual(line["duration_ms"], 2.5)
        self.assertIn("timestamp", line)


if __name__ == "__main__":
    unittest.main()

"""Tests for app.alerts — webhook notification sender."""

from unittest.mock import MagicMock, patch

import requests


class TestSendAlert:

    def test_no_webhook_url_skips(self):
        with patch("app.alerts.WEBHOOK_URL", ""), \
             patch("app.alerts.requests.post") as mock_post:
            from app.alerts import send_alert
            send_alert("Test", "msg")
            mock_post.assert_not_called()

    def test_success_sends_webhook(self):
        with patch("app.alerts.WEBHOOK_URL", "https://hooks.slack.com/test"), \
             patch("app.alerts.requests.post") as mock_post:
            mock_post.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
            from app.alerts import send_alert
            send_alert("Pipeline OK", "Done", status="success")
        payload = mock_post.call_args[1]["json"]
        assert payload["title"] == "Pipeline OK" and payload["status"] == "success"

    def test_http_failure_does_not_raise(self):
        with patch("app.alerts.WEBHOOK_URL", "https://hooks.slack.com/test"), \
             patch("app.alerts.requests.post", side_effect=requests.RequestException("fail")):
            from app.alerts import send_alert
            send_alert("Test", "msg")  # should not raise
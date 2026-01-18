"""Tests for Slack notification tasks."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cci_slack.tasks import SlackNotify, SlackNotifyFlowResult, send_slack_message


class TestSendSlackMessage:
    """Tests for the send_slack_message function."""

    @patch("cci_slack.tasks.requests")
    def test_send_simple_message(self, mock_requests):
        """Test sending a simple text message."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        result = send_slack_message(
            webhook_url="https://hooks.slack.com/test",
            message="Hello, World!",
        )

        assert result["status"] == "ok"
        mock_requests.post.assert_called_once()

        call_args = mock_requests.post.call_args
        payload = json.loads(call_args[1]["data"])
        assert payload["text"] == "Hello, World!"

    @patch("cci_slack.tasks.requests")
    def test_send_message_with_all_options(self, mock_requests):
        """Test sending a message with all optional parameters."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        result = send_slack_message(
            webhook_url="https://hooks.slack.com/test",
            message="Test message",
            channel="#test-channel",
            username="TestBot",
            icon_emoji=":robot:",
        )

        assert result["status"] == "ok"

        call_args = mock_requests.post.call_args
        payload = json.loads(call_args[1]["data"])

        assert payload["text"] == "Test message"
        assert payload["channel"] == "#test-channel"
        assert payload["username"] == "TestBot"
        assert payload["icon_emoji"] == ":robot:"

    @patch("cci_slack.tasks.requests")
    def test_send_message_with_attachments(self, mock_requests):
        """Test sending a message with attachments."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        attachments = [
            {
                "color": "good",
                "fields": [{"title": "Test", "value": "Value"}],
            }
        ]

        result = send_slack_message(
            webhook_url="https://hooks.slack.com/test",
            message="Message with attachment",
            attachments=attachments,
        )

        assert result["status"] == "ok"

        call_args = mock_requests.post.call_args
        payload = json.loads(call_args[1]["data"])

        assert payload["attachments"] == attachments

    @patch("cci_slack.tasks.requests")
    def test_request_headers(self, mock_requests):
        """Test that correct headers are sent."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        send_slack_message(
            webhook_url="https://hooks.slack.com/test",
            message="Test",
        )

        call_args = mock_requests.post.call_args
        assert call_args[1]["headers"]["Content-Type"] == "application/json"
        assert call_args[1]["timeout"] == 30


class TestSlackNotifyTask:
    """Tests for the SlackNotify task."""

    def _create_task(self, options):
        """Helper to create a task with mocked dependencies."""
        mock_project_config = MagicMock()
        mock_project_config.keychain = None

        mock_task_config = MagicMock()
        mock_task_config.options = options

        mock_org_config = MagicMock()

        task = SlackNotify(mock_project_config, mock_task_config, mock_org_config)
        task.logger = MagicMock()
        return task

    @patch("cci_slack.tasks.requests")
    def test_run_task_with_webhook_url_option(self, mock_requests):
        """Test running task with webhook_url provided as option."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        task = self._create_task(
            {
                "message": "Test notification",
                "webhook_url": "https://hooks.slack.com/test",
            }
        )

        result = task._run_task()

        assert result["status"] == "ok"
        task.logger.info.assert_called()

    @patch("cci_slack.tasks.requests")
    def test_run_task_with_channel_override(self, mock_requests):
        """Test running task with channel override."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        task = self._create_task(
            {
                "message": "Alert!",
                "webhook_url": "https://hooks.slack.com/test",
                "channel": "#alerts",
                "icon_emoji": ":warning:",
            }
        )

        task._run_task()

        call_args = mock_requests.post.call_args
        payload = json.loads(call_args[1]["data"])

        assert payload["channel"] == "#alerts"
        assert payload["icon_emoji"] == ":warning:"

    def test_get_webhook_url_from_service(self):
        """Test getting webhook URL from slack service."""
        mock_project_config = MagicMock()
        mock_service = MagicMock()
        mock_service.config = {"webhook_url": "https://hooks.slack.com/from-service"}
        mock_project_config.keychain.get_service.return_value = mock_service

        mock_task_config = MagicMock()
        mock_task_config.options = {"message": "Test"}

        task = SlackNotify(mock_project_config, mock_task_config, MagicMock())

        webhook_url = task._get_webhook_url()

        assert webhook_url == "https://hooks.slack.com/from-service"
        mock_project_config.keychain.get_service.assert_called_with("slack")

    def test_get_webhook_url_missing_raises_error(self):
        """Test that missing webhook URL raises ValueError."""
        mock_project_config = MagicMock()
        mock_project_config.keychain.get_service.side_effect = Exception("Not found")

        mock_task_config = MagicMock()
        mock_task_config.options = {"message": "Test"}

        task = SlackNotify(mock_project_config, mock_task_config, MagicMock())

        with pytest.raises(ValueError, match="Slack webhook URL not configured"):
            task._get_webhook_url()


class TestSlackNotifyFlowResultTask:
    """Tests for the SlackNotifyFlowResult task."""

    def _create_task(self, options):
        """Helper to create a task with mocked dependencies."""
        mock_project_config = MagicMock()
        mock_project_config.keychain = None

        mock_task_config = MagicMock()
        mock_task_config.options = options

        mock_org_config = MagicMock()

        task = SlackNotifyFlowResult(
            mock_project_config, mock_task_config, mock_org_config
        )
        task.logger = MagicMock()
        return task

    @patch("cci_slack.tasks.requests")
    def test_successful_flow_notification(self, mock_requests):
        """Test notification for successful flow."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        task = self._create_task(
            {
                "flow_name": "dev_org",
                "success": "True",
                "duration": "5m 30s",
                "org_name": "dev",
                "webhook_url": "https://hooks.slack.com/test",
            }
        )

        task._run_task()

        call_args = mock_requests.post.call_args
        payload = json.loads(call_args[1]["data"])

        assert ":white_check_mark:" in payload["text"]
        assert "succeeded" in payload["text"]
        assert payload["attachments"][0]["color"] == "good"

    @patch("cci_slack.tasks.requests")
    def test_failed_flow_notification(self, mock_requests):
        """Test notification for failed flow."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        task = self._create_task(
            {
                "flow_name": "ci_feature",
                "success": "False",
                "duration": "2m 15s",
                "webhook_url": "https://hooks.slack.com/test",
            }
        )

        task._run_task()

        call_args = mock_requests.post.call_args
        payload = json.loads(call_args[1]["data"])

        assert ":x:" in payload["text"]
        assert "failed" in payload["text"]
        assert payload["attachments"][0]["color"] == "danger"

    @patch("cci_slack.tasks.requests")
    def test_attachment_fields(self, mock_requests):
        """Test that attachment contains correct fields."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        task = self._create_task(
            {
                "flow_name": "deploy",
                "success": "True",
                "duration": "10m",
                "org_name": "production",
                "webhook_url": "https://hooks.slack.com/test",
            }
        )

        task._run_task()

        call_args = mock_requests.post.call_args
        payload = json.loads(call_args[1]["data"])

        fields = payload["attachments"][0]["fields"]
        field_titles = [f["title"] for f in fields]

        assert "Flow" in field_titles
        assert "Status" in field_titles
        assert "Duration" in field_titles
        assert "Org" in field_titles

    @patch("cci_slack.tasks.requests")
    def test_with_details(self, mock_requests):
        """Test notification with additional details."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        task = self._create_task(
            {
                "flow_name": "ci_feature",
                "success": "False",
                "details": "Test failure in TestClass.test_method",
                "webhook_url": "https://hooks.slack.com/test",
            }
        )

        task._run_task()

        call_args = mock_requests.post.call_args
        payload = json.loads(call_args[1]["data"])

        assert payload["attachments"][0]["text"] == "Test failure in TestClass.test_method"

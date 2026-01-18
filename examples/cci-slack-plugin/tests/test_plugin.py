"""Tests for the CCI Slack plugin class."""

import json
from unittest.mock import MagicMock, patch

import pytest

from cci_slack import CCISlackPlugin


class TestCCISlackPlugin:
    """Tests for the CCISlackPlugin class."""

    def test_manifest_name(self):
        """Test that manifest has correct name."""
        plugin = CCISlackPlugin()
        assert plugin.manifest.name == "cci-slack"

    def test_manifest_version(self):
        """Test that manifest has a version."""
        plugin = CCISlackPlugin()
        assert plugin.manifest.version == "1.0.0"

    def test_manifest_tasks(self):
        """Test that manifest registers expected tasks."""
        plugin = CCISlackPlugin()
        tasks = plugin.manifest.tasks

        assert "slack_notify" in tasks
        assert "slack_notify_flow_result" in tasks
        assert tasks["slack_notify"] == "cci_slack.tasks.SlackNotify"

    def test_manifest_flows(self):
        """Test that manifest registers expected flows."""
        plugin = CCISlackPlugin()
        flows = plugin.manifest.flows

        assert "notify_dev_org" in flows
        assert flows["notify_dev_org"]["description"] == "Set up dev org and notify via Slack"

    def test_manifest_services(self):
        """Test that manifest registers slack service."""
        plugin = CCISlackPlugin()
        services = plugin.manifest.services

        assert "slack" in services
        assert "webhook_url" in services["slack"]["attributes"]
        assert services["slack"]["attributes"]["webhook_url"]["required"] is True

    def test_manifest_min_cci_version(self):
        """Test that manifest specifies minimum CCI version."""
        plugin = CCISlackPlugin()
        assert plugin.manifest.min_cci_version == "4.5.0"

    def test_on_load_sets_runtime(self):
        """Test that on_load sets the runtime."""
        plugin = CCISlackPlugin()
        mock_runtime = MagicMock()

        plugin.on_load(mock_runtime)

        assert plugin.runtime == mock_runtime


class TestPluginHooks:
    """Tests for plugin hook implementations."""

    @patch("cci_slack.tasks.requests")
    def test_cci_flow_complete_sends_notification(self, mock_requests):
        """Test that cci_flow_complete hook sends Slack notification."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        plugin = CCISlackPlugin()
        plugin._config = {
            "auto_notify_flows": True,
            "webhook_url": "https://hooks.slack.com/test",
        }

        mock_flow = MagicMock()
        result = {"flow_name": "dev_org", "success": True}

        plugin.cci_flow_complete(flow=mock_flow, result=result)

        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        payload = json.loads(call_args[1]["data"])

        assert ":white_check_mark:" in payload["text"]
        assert "dev_org" in payload["text"]
        assert "completed successfully" in payload["text"]

    @patch("cci_slack.tasks.requests")
    def test_cci_flow_complete_failed_flow(self, mock_requests):
        """Test notification for failed flow."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        plugin = CCISlackPlugin()
        plugin._config = {
            "auto_notify_flows": True,
            "webhook_url": "https://hooks.slack.com/test",
        }

        result = {"flow_name": "ci_feature", "success": False}

        plugin.cci_flow_complete(flow=MagicMock(), result=result)

        call_args = mock_requests.post.call_args
        payload = json.loads(call_args[1]["data"])

        assert ":x:" in payload["text"]
        assert "failed" in payload["text"]

    def test_cci_flow_complete_disabled(self):
        """Test that hook does nothing when auto_notify_flows is False."""
        plugin = CCISlackPlugin()
        plugin._config = {"auto_notify_flows": False}

        # Should not raise and should not attempt to send
        with patch("cci_slack.tasks.requests") as mock_requests:
            plugin.cci_flow_complete(flow=MagicMock(), result={"success": True})
            mock_requests.post.assert_not_called()

    def test_cci_flow_complete_no_webhook(self):
        """Test that hook handles missing webhook gracefully."""
        plugin = CCISlackPlugin()
        plugin._config = {"auto_notify_flows": True}
        plugin._runtime = None

        # Should not raise
        with patch("cci_slack.tasks.requests") as mock_requests:
            plugin.cci_flow_complete(
                flow=MagicMock(), result={"flow_name": "test", "success": True}
            )
            mock_requests.post.assert_not_called()

    @patch("cci_slack.tasks.requests")
    def test_cci_task_complete_sends_notification(self, mock_requests):
        """Test that cci_task_complete hook sends notification for configured tasks."""
        mock_response = MagicMock()
        mock_response.text = "ok"
        mock_requests.post.return_value = mock_response

        plugin = CCISlackPlugin()
        plugin._config = {
            "notify_on_tasks": ["deploy", "run_tests"],
            "webhook_url": "https://hooks.slack.com/test",
        }

        mock_task = MagicMock()
        mock_task.name = "deploy"
        result = {"success": True}

        plugin.cci_task_complete(task=mock_task, result=result)

        mock_requests.post.assert_called_once()
        call_args = mock_requests.post.call_args
        payload = json.loads(call_args[1]["data"])

        assert "deploy" in payload["text"]
        assert "completed" in payload["text"]

    def test_cci_task_complete_ignores_unconfigured_tasks(self):
        """Test that hook ignores tasks not in notify_on_tasks list."""
        plugin = CCISlackPlugin()
        plugin._config = {
            "notify_on_tasks": ["deploy"],
            "webhook_url": "https://hooks.slack.com/test",
        }

        mock_task = MagicMock()
        mock_task.name = "some_other_task"

        with patch("cci_slack.tasks.requests") as mock_requests:
            plugin.cci_task_complete(task=mock_task, result={"success": True})
            mock_requests.post.assert_not_called()


class TestPluginWebhookUrl:
    """Tests for webhook URL retrieval."""

    def test_get_webhook_url_from_config(self):
        """Test getting webhook URL from plugin config."""
        plugin = CCISlackPlugin()
        plugin._config = {"webhook_url": "https://hooks.slack.com/from-config"}

        url = plugin._get_webhook_url()

        assert url == "https://hooks.slack.com/from-config"

    def test_get_webhook_url_from_service(self):
        """Test getting webhook URL from slack service."""
        plugin = CCISlackPlugin()
        plugin._config = {}

        mock_service = MagicMock()
        mock_service.config = {"webhook_url": "https://hooks.slack.com/from-service"}

        mock_keychain = MagicMock()
        mock_keychain.get_service.return_value = mock_service

        mock_runtime = MagicMock()
        mock_runtime.keychain = mock_keychain

        plugin._runtime = mock_runtime

        url = plugin._get_webhook_url()

        assert url == "https://hooks.slack.com/from-service"

    def test_get_webhook_url_returns_none_when_unavailable(self):
        """Test that None is returned when no webhook URL is available."""
        plugin = CCISlackPlugin()
        plugin._config = {}
        plugin._runtime = None

        url = plugin._get_webhook_url()

        assert url is None

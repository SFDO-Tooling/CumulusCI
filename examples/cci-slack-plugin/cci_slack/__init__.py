"""CCI Slack Plugin - Slack notifications for CumulusCI.

This plugin provides:
- Slack notification tasks
- Hooks for automatic notifications on flow/task completion
- A Slack service for storing webhook configuration
"""

import logging

from cumulusci.core.plugins import CCIPlugin, PluginManifest, TrustLevel
from cumulusci.core.plugins.hooks import hookimpl

logger = logging.getLogger(__name__)


class CCISlackPlugin(CCIPlugin):
    """CumulusCI plugin for Slack notifications."""

    @property
    def manifest(self) -> PluginManifest:
        return PluginManifest(
            name="cci-slack",
            version="1.0.0",
            description="Slack notifications for CumulusCI flows and tasks",
            author="Your Name",
            homepage="https://github.com/yourname/cci-slack",
            # Register custom tasks
            tasks={
                "slack_notify": "cci_slack.tasks.SlackNotify",
                "slack_notify_flow_result": "cci_slack.tasks.SlackNotifyFlowResult",
            },
            # Register custom flows
            flows={
                "notify_dev_org": {
                    "description": "Set up dev org and notify via Slack",
                    "steps": {
                        "1": {"flow": "dev_org"},
                        "2": {
                            "task": "@cci-slack:slack_notify",
                            "options": {"message": "Dev org setup completed!"},
                        },
                    },
                },
            },
            # Register custom service for Slack credentials
            services={
                "slack": {
                    "description": "Slack webhook configuration",
                    "attributes": {
                        "webhook_url": {
                            "description": "Slack Incoming Webhook URL",
                            "required": True,
                            "sensitive": True,
                        },
                        "default_channel": {
                            "description": "Default channel for notifications",
                            "required": False,
                            "default": "#builds",
                        },
                        "username": {
                            "description": "Bot username for messages",
                            "required": False,
                            "default": "CumulusCI",
                        },
                    },
                },
            },
            # This plugin only needs standard trust level
            required_trust_level=TrustLevel.STANDARD,
            # Minimum CumulusCI version required
            min_cci_version="4.5.0",
        )

    def on_load(self, runtime):
        """Called when the plugin is loaded."""
        self.runtime = runtime
        logger.debug("CCI Slack plugin loaded")

    def on_unload(self):
        """Called when the plugin is unloaded."""
        logger.debug("CCI Slack plugin unloaded")

    # --- Hook implementations for automatic notifications ---

    @hookimpl
    def cci_flow_complete(self, flow, result):  # noqa: ARG002
        """Send Slack notification when a flow completes."""
        # Only notify if auto_notify is enabled in plugin config
        if not self.config.get("auto_notify_flows", False):
            return

        try:
            from cci_slack.tasks import send_slack_message

            webhook_url = self._get_webhook_url()
            if not webhook_url:
                return

            flow_name = result.get("flow_name", "Unknown flow")
            success = result.get("success", False)
            emoji = ":white_check_mark:" if success else ":x:"
            status = "completed successfully" if success else "failed"

            message = f"{emoji} Flow `{flow_name}` {status}"
            send_slack_message(webhook_url, message)

        except Exception as e:
            logger.warning(f"Failed to send Slack notification: {e}")

    @hookimpl
    def cci_task_complete(self, task, result):
        """Send Slack notification when specific tasks complete."""
        # Only notify for tasks in the notify list
        notify_tasks = self.config.get("notify_on_tasks", [])
        task_name = getattr(task, "name", None)

        if not task_name or task_name not in notify_tasks:
            return

        try:
            from cci_slack.tasks import send_slack_message

            webhook_url = self._get_webhook_url()
            if not webhook_url:
                return

            success = result.get("success", True)
            emoji = ":white_check_mark:" if success else ":x:"
            status = "completed" if success else "failed"

            message = f"{emoji} Task `{task_name}` {status}"
            send_slack_message(webhook_url, message)

        except Exception as e:
            logger.warning(f"Failed to send Slack notification: {e}")

    def _get_webhook_url(self):
        """Get Slack webhook URL from service or config."""
        # First try plugin config
        webhook_url = self.config.get("webhook_url")
        if webhook_url:
            return webhook_url

        # Then try the slack service
        try:
            if hasattr(self, "runtime") and self.runtime:
                keychain = getattr(self.runtime, "keychain", None)
                if keychain:
                    service = keychain.get_service("slack")
                    return service.config.get("webhook_url")
        except Exception:
            pass

        return None

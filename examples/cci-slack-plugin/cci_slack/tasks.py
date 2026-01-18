"""Slack notification tasks for CumulusCI."""

import json
from typing import Optional

import requests

from cumulusci.core.tasks import BaseTask


def send_slack_message(
    webhook_url: str,
    message: str,
    channel: Optional[str] = None,
    username: Optional[str] = None,
    icon_emoji: Optional[str] = None,
    attachments: Optional[list] = None,
) -> dict:
    """Send a message to Slack via webhook.

    Args:
        webhook_url: Slack Incoming Webhook URL
        message: The message text to send
        channel: Override the default channel (optional)
        username: Override the default username (optional)
        icon_emoji: Emoji to use as the icon (optional)
        attachments: List of Slack attachment objects (optional)

    Returns:
        Response data from Slack API
    """
    payload = {"text": message}

    if channel:
        payload["channel"] = channel
    if username:
        payload["username"] = username
    if icon_emoji:
        payload["icon_emoji"] = icon_emoji
    if attachments:
        payload["attachments"] = attachments

    response = requests.post(
        webhook_url,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"},
        timeout=30,
    )
    response.raise_for_status()

    return {"status": "ok", "response": response.text}


class SlackNotify(BaseTask):
    """Send a notification message to Slack.

    This task sends a simple text message to a Slack channel
    using an Incoming Webhook.

    Example usage:
        cci task run @cci-slack:slack_notify -o message "Deployment complete!"
        cci task run @cci-slack:slack_notify -o message "Build failed" -o channel "#alerts"
    """

    task_docs = """
    Send a notification to Slack.

    Requires the 'slack' service to be configured with a webhook URL,
    or the webhook_url option to be provided directly.
    """

    task_options = {
        "message": {
            "description": "The message to send to Slack",
            "required": True,
        },
        "channel": {
            "description": "Override the default Slack channel (e.g., #builds)",
            "required": False,
        },
        "username": {
            "description": "Override the bot username",
            "required": False,
        },
        "icon_emoji": {
            "description": "Emoji to use as the bot icon (e.g., :rocket:)",
            "required": False,
        },
        "webhook_url": {
            "description": "Slack webhook URL (overrides service config)",
            "required": False,
        },
    }

    def _get_webhook_url(self) -> str:
        """Get the Slack webhook URL from options or service."""
        # First check if provided directly as option
        if self.options.get("webhook_url"):
            return self.options["webhook_url"]

        # Otherwise get from slack service
        try:
            service = self.project_config.keychain.get_service("slack")
            return service.config["webhook_url"]
        except Exception as e:
            raise ValueError(
                "Slack webhook URL not configured. Either provide --webhook_url "
                "or configure the slack service with: cci service connect slack"
            ) from e

    def _run_task(self):
        """Execute the Slack notification task."""
        webhook_url = self._get_webhook_url()
        message = self.options["message"]

        self.logger.info(f"Sending Slack notification: {message[:50]}...")

        result = send_slack_message(
            webhook_url=webhook_url,
            message=message,
            channel=self.options.get("channel"),
            username=self.options.get("username"),
            icon_emoji=self.options.get("icon_emoji"),
        )

        self.logger.info("Slack notification sent successfully")
        return result


class SlackNotifyFlowResult(BaseTask):
    """Send a formatted flow result notification to Slack.

    This task sends a rich notification with flow execution details,
    including success/failure status, duration, and step information.

    Example usage:
        cci task run @cci-slack:slack_notify_flow_result \\
            -o flow_name "dev_org" \\
            -o success True \\
            -o duration "2m 30s"
    """

    task_docs = """
    Send a formatted flow result notification to Slack.

    Creates a rich message with attachments showing flow execution details.
    """

    task_options = {
        "flow_name": {
            "description": "Name of the flow that was executed",
            "required": True,
        },
        "success": {
            "description": "Whether the flow succeeded (True/False)",
            "required": True,
        },
        "duration": {
            "description": "How long the flow took to execute",
            "required": False,
        },
        "org_name": {
            "description": "Name of the org the flow ran against",
            "required": False,
        },
        "details": {
            "description": "Additional details to include in the message",
            "required": False,
        },
        "webhook_url": {
            "description": "Slack webhook URL (overrides service config)",
            "required": False,
        },
    }

    def _get_webhook_url(self) -> str:
        """Get the Slack webhook URL from options or service."""
        if self.options.get("webhook_url"):
            return self.options["webhook_url"]

        try:
            service = self.project_config.keychain.get_service("slack")
            return service.config["webhook_url"]
        except Exception as e:
            raise ValueError(
                "Slack webhook URL not configured. Either provide --webhook_url "
                "or configure the slack service with: cci service connect slack"
            ) from e

    def _run_task(self):
        """Execute the flow result notification task."""
        webhook_url = self._get_webhook_url()

        flow_name = self.options["flow_name"]
        success = str(self.options["success"]).lower() in ("true", "1", "yes")
        duration = self.options.get("duration", "N/A")
        org_name = self.options.get("org_name", "N/A")
        details = self.options.get("details", "")

        # Build the message
        if success:
            color = "good"  # Green
            emoji = ":white_check_mark:"
            status = "succeeded"
        else:
            color = "danger"  # Red
            emoji = ":x:"
            status = "failed"

        message = f"{emoji} Flow `{flow_name}` {status}"

        # Build attachment with details
        fields = [
            {"title": "Flow", "value": flow_name, "short": True},
            {"title": "Status", "value": status.capitalize(), "short": True},
            {"title": "Duration", "value": duration, "short": True},
            {"title": "Org", "value": org_name, "short": True},
        ]

        attachments = [
            {
                "color": color,
                "fields": fields,
                "footer": "CumulusCI",
                "ts": int(__import__("time").time()),
            }
        ]

        if details:
            attachments[0]["text"] = details

        self.logger.info(f"Sending flow result notification for: {flow_name}")

        result = send_slack_message(
            webhook_url=webhook_url,
            message=message,
            attachments=attachments,
        )

        self.logger.info("Flow result notification sent successfully")
        return result

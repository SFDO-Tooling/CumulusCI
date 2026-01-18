# CCI Slack Plugin

A CumulusCI plugin that provides Slack notification capabilities for your CI/CD workflows.

## Features

- **Slack Notification Tasks**: Send messages to Slack channels
- **Flow Result Notifications**: Rich formatted notifications with flow execution details
- **Automatic Notifications**: Hook-based notifications on flow/task completion
- **Slack Service**: Store webhook configuration securely

## Installation

```bash
pip install cci-slack
```

Or install from source:

```bash
cd examples/cci-slack-plugin
pip install -e .
```

## Configuration

### 1. Connect the Slack Service

First, create a [Slack Incoming Webhook](https://api.slack.com/messaging/webhooks) for your workspace.

Then connect the service:

```bash
cci service connect slack
```

You'll be prompted for:
- **webhook_url**: Your Slack Incoming Webhook URL
- **default_channel**: Default channel for notifications (e.g., `#builds`)
- **username**: Bot username (default: `CumulusCI`)

### 2. Enable the Plugin

Add to your `cumulusci.yml`:

```yaml
plugins:
  cci-slack:
    enabled: true
    config:
      # Optional: Enable automatic flow notifications
      auto_notify_flows: true
      # Optional: Notify on specific task completions
      notify_on_tasks:
        - deploy
        - run_tests
```

## Usage

### Send a Simple Notification

```bash
# Using the task directly
cci task run @cci-slack:slack_notify -o message "Deployment complete!"

# With channel override
cci task run @cci-slack:slack_notify \
  -o message "Build failed!" \
  -o channel "#alerts" \
  -o icon_emoji ":warning:"
```

### Send Flow Result Notification

```bash
cci task run @cci-slack:slack_notify_flow_result \
  -o flow_name "dev_org" \
  -o success True \
  -o duration "2m 30s" \
  -o org_name "dev"
```

### Use in a Flow

Add Slack notifications to your flows in `cumulusci.yml`:

```yaml
flows:
  deploy_and_notify:
    steps:
      1:
        flow: dev_org
      2:
        task: "@cci-slack:slack_notify"
        options:
          message: "Dev org setup complete!"
          channel: "#dev-builds"
```

## Plugin Configuration Options

In `cumulusci.yml`:

```yaml
plugins:
  cci-slack:
    enabled: true
    trust_level: standard  # Only needs standard trust
    config:
      # Webhook URL (alternative to using the service)
      webhook_url: ${SLACK_WEBHOOK_URL}

      # Automatic notifications
      auto_notify_flows: true

      # Notify when these tasks complete
      notify_on_tasks:
        - deploy
        - run_tests
        - upload_beta
```

## Tasks Reference

### slack_notify

Send a simple message to Slack.

| Option | Required | Description |
|--------|----------|-------------|
| message | Yes | The message to send |
| channel | No | Override default channel |
| username | No | Override bot username |
| icon_emoji | No | Emoji for bot icon |
| webhook_url | No | Override service webhook URL |

### slack_notify_flow_result

Send a formatted flow result notification.

| Option | Required | Description |
|--------|----------|-------------|
| flow_name | Yes | Name of the executed flow |
| success | Yes | Whether the flow succeeded |
| duration | No | Execution duration |
| org_name | No | Target org name |
| details | No | Additional details |
| webhook_url | No | Override service webhook URL |

## Development

### Running Tests

```bash
pip install -e ".[dev]"
pytest
```

### Building

```bash
pip install build
python -m build
```

## License

BSD-3-Clause

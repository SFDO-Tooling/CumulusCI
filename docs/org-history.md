# Org History Tracking in CumulusCI

## Overview

Org History Tracking is a powerful feature in CumulusCI that provides comprehensive observability and auditing capabilities for all actions performed against Salesforce orgs. This feature allows you to maintain a detailed record of tasks, flows, and other operations, enabling better troubleshooting, compliance, and optimization of your Salesforce development processes.

CumulusCI has always excelled at performing dynamic work behind the scenes, streamlining many aspects of Salesforce development. However, understanding the specifics of these automated processes has traditionally been challenging. The Org History Tracking feature changes this by providing visibility into both the inputs you provide and the calculated actions that CumulusCI performs against your orgs.

## Enabling Org History Tracking

To enable Org History Tracking for a scratch org, add the `track_history` option to your org's configuration in the `cumulusci.yml` file:

```yaml
orgs:
    scratch:
        dev: # or other org name
            # ... other configuration options ...
            track_history: True
```

You can also enable or disable history tracking for an org using the CLI:

```
cci history enable [ORGNAME]
cci history disable [ORGNAME]
```

## Data Tracked

Org History Tracking captures a wide range of data for each action performed.

Org History is part of the CumulusCI OrgConfig and is stored encrypted in the CumulusCI keychain. No Org History data is sent externally.

The top-level OrgActionResult models include:

### BaseOrgActionResult

-   `hash_action`: A unique hash for the action instance
-   `hash_config`: A unique hash representing the action instance's configuration
-   `duration`: The duration of the action
-   `status`: The status of the action (success, failure, error)
-   `log`: The log output of the action
-   `exception`: The exception message if the action failed

### TaskOrgAction (inherits from BaseOrgActionResult)

-   `name`: The name of the task
-   `description`: The description of the task
-   `group`: The group of the task
-   `class_path`: The class of the task
-   `options`: The options passed to the task
-   `parsed_options`: The options after being parsed by the task
-   `files`: File references used by the task
-   `directories`: Directory references used by the task
-   `commands`: Commands executed by the task
-   `deploys`: Metadata deployments executed by the task
-   `retrieves`: Metadata retrievals executed by the task
-   `transforms`: Metadata transformations executed by the task
-   `package_installs`: Package installs executed by the task
-   `return_values`: The return values of the task

TaskOrgAction provides detailed tracking of various operations, including:

-   File and directory references
-   Metadata API interactions (retrieve/deploy/transform)
-   Package installations
-   Command executions

Each of these references is tracked and hashed for later comparison, providing a comprehensive view of the task's operations.

### FlowOrgAction (inherits from BaseOrgActionResult)

-   `name`: The name of the flow
-   `description`: The description of the flow
-   `group`: The group of the flow
-   `config_steps`: The flow configuration
-   `steps`: The details and results from all steps in the flow

### Other Action Types

-   `OrgCreateAction`: Tracks org creation details
-   `OrgConnectAction`: Tracks org connection details
-   `OrgDeleteAction`: Tracks org deletion details
-   `OrgImportAction`: Tracks org import details

## Command Reference

### Listing Org History

```
cci history list [ORGNAME] [OPTIONS]
```

Display the history of actions for an org.

Options:

-   `--action-type TEXT`: Filter by action types (comma-separated)
-   `--status TEXT`: Filter by status (success, failure, error)
-   `--before TEXT` / `--after TEXT`: Include actions before/after a specific action hash
-   `--action-hash TEXT` / `--config-hash TEXT`: Filter by specific action or config hashes
-   `--exclude-action-hash TEXT` / `--exclude-config-hash TEXT`: Exclude specific hashes
-   `--org-id TEXT`: List actions for a previous org instance
-   `--json`: Output in JSON format

### Viewing Action Details

```
cci history info ACTION_HASH [ORGNAME] [OPTIONS]
```

Display detailed information about a specific action.

Options:

-   `--json`: Output in JSON format

### Clearing History

```
cci history clear [ORGNAME] [OPTIONS]
```

Clear part or all of an org's history.

Options:

-   `--all`: Clear all history
-   `--before TEXT` / `--after TEXT`: Clear history before/after a specific action hash
-   `--hash TEXT`: Clear a specific action from the history

### Viewing Previous Org Instances

```
cci history previous [ORGNAME] [OPTIONS]
```

List previous instances of an org and summarize their history.

### Replaying Actions

```
cci history replay [ORGNAME] [OPTIONS]
```

Replay a sequence of actions from the org's history.

Options:

-   Similar filtering options to `cci history list`
-   `--no-prompts`: Skip all prompts during replay
-   `--dry-run`: Simulate the replay without actually performing actions

## Best Practices

1. **Regular Review**: Periodically review your org's history to understand patterns and identify potential issues.
2. **Compliance**: Use the detailed history for audit trails and compliance reporting.
3. **Troubleshooting**: When issues arise, use the history to understand recent changes and their impacts.
4. **Optimization**: Analyze action durations and patterns to optimize your development and deployment processes.
5. **Documentation**: Use the history as a basis for automatically generating documentation of org changes over time.

## Limitations and Considerations

-   History tracking may have a small performance impact and increase storage requirements.
-   Sensitive information in command outputs is automatically redacted, but always review before sharing histories.
-   History is stored with the org's configuration and is not automatically synced across different development environments.

## Understanding Task Options

CumulusCI tasks often perform dynamic calculations based on the options you provide. The Org History Tracking feature gives you visibility into both the original options you passed to a task (`options`) and the calculated options that the task actually used (`parsed_options`). This can be particularly useful for understanding how CumulusCI interprets and processes your inputs.

For example, if your project is using CumulusCI's dynamic dependencies to install a product from another GitHub repository, like NPSP:

```
cci task run update_dependencies
```

The history will show track two sets of options:

-   `options`: the original options you provided, in this case none so the default project dependencies specified under `project -> dependencies` in the cumulusci.yml file are used
-   `parsed_options`: the dynamically resolved options the task calculated and used for excution. In this case, that's the results of the dyanmic resolution of NPSP and all its latest dependencies.

This can help you understand how CumulusCI is interpreting your inputs and what additional default values or calculations it's applying.

## Future Enhancements (Proposed)

-   A mechanism for custom code to hook into OrgAction events
-   Advanced search and filtering capabilities for large histories
-   Visual timeline representation of org history

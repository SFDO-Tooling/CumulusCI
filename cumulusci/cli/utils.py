from collections import defaultdict


def get_available_tasks(runtime):
    return (
        runtime.project_config.list_tasks()
        if runtime.project_config is not None
        else runtime.universal_config.list_tasks()
    )


def get_available_flows(runtime):
    return (
        runtime.project_config.list_flows()
        if runtime.project_config is not None
        else runtime.universal_config.list_flows()
    )


def group_items(items):
    """Given a list of dicts with 'group' keys,
    returns those items in lists categorized group"""
    groups = defaultdict(list)
    for item in items:
        group_name = item["group"] or "Other"
        groups[group_name].append([item["name"], item["description"]])

    return groups

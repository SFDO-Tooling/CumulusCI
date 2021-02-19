from collections import defaultdict


def group_items(items):
    """Given a list of dicts with 'group' keys,
    returns those items in lists categorized group"""
    groups = defaultdict(list)
    for item in items:
        group_name = item["group"] or "Other"
        groups[group_name].append([item["name"], item["description"]])

    return groups

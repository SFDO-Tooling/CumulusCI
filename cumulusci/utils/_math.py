def clip(value, min_=None, max_=None):
    """Clip a value to a range."""
    if min_ is not None:
        value = max(value, min_)
    if max_ is not None:
        value = min(value, max_)
    return value

from builtins import bytes, int, str
from collections import OrderedDict

from cumulusci.core.exceptions import ConfigMergeError


def merge_config(configs):
    new_config = {}

    for name in reversed(OrderedDict(configs)):
        new_config = dictmerge(new_config, configs[name], name)

    return new_config


def dictmerge(a, b, name=None):
    """ Deeply merge two ``dict``s that consist of lists, dicts, and scalars.
    This function (recursively) merges ``b`` INTO ``a``, does not copy any values, and returns ``a``.

    based on https://stackoverflow.com/a/15836901/5042831
    NOTE: tuples and arbitrary objects are NOT handled and will raise TypeError """

    key = None

    if b is None:
        return a

    try:
        if a is None or isinstance(a, (bytes, int, str, float)):
            # first run, or if ``a``` is a scalar
            a = b
        elif isinstance(a, list):
            # lists can be only appended
            if isinstance(b, list):
                # merge lists
                a.extend(b)
            else:
                # append to list
                a.append(b)
        elif isinstance(a, dict):
            # dicts must be merged
            if isinstance(b, dict):
                for key in b:
                    if key in a:
                        a[key] = dictmerge(a[key], b[key], name)
                    else:
                        a[key] = b[key]
            else:
                raise TypeError(
                    'Cannot merge non-dict of type "{}" into dict "{}"'.format(
                        type(b), a
                    )
                )
        else:
            raise TypeError(
                'dictmerge does not supporting merging "{}" into "{}"'.format(
                    type(b), type(a)
                )
            )
    except TypeError as e:
        raise ConfigMergeError(
            'TypeError "{}" in key "{}" when merging "{}" into "{}"'.format(
                e, key, type(b), type(a)
            ),
            config_name=name,
        )
    return a

""" Utilities for CumulusCI Core"""

import copy
import glob
import time
import typing as T
import warnings
from datetime import datetime, timedelta

import pytz

from cumulusci.core.exceptions import ConfigMergeError, TaskOptionsError


def import_global(path: str):
    """Import a class from a string module class path"""
    components = path.split(".")
    module = components[:-1]
    module = ".".join(module)
    mod = __import__(module, fromlist=[str(components[-1])])
    return getattr(mod, str(components[-1]))


# For backwards-compatibility
import_class = import_global


def parse_datetime(dt_str, format):
    """Create a timezone-aware datetime object from a datetime string."""
    t = time.strptime(dt_str, format)
    return datetime(t[0], t[1], t[2], t[3], t[4], t[5], t[6], pytz.UTC)


def process_bool_arg(arg: T.Union[int, str, None]):
    """Determine True/False from argument.

    Similar to parts of the Salesforce API, there are a few true-ish and false-ish strings,
        but "True" and "False" are the canonical ones.

    None is accepted as "False" for backwards compatiblity reasons, but this usage is deprecated.
    """
    if isinstance(arg, (int, bool)):
        return bool(arg)
    elif arg is None:
        # backwards compatible behaviour that some tasks
        # rely upon.
        import traceback

        warnings.warn("".join(traceback.format_stack(limit=4)), DeprecationWarning)
        warnings.warn(
            "Future versions of CCI will not accept 'None' as an argument to process_bool_arg",
            DeprecationWarning,
        )

        return False
    elif isinstance(arg, str):
        # these are values that Salesforce's bulk loader accepts
        # there doesn't seem to be any harm in acccepting the
        # full list to be coordinated with a "Salesforce standard"
        if arg.lower() in ["yes", "y", "true", "on", "1"]:
            return True
        elif arg.lower() in ["no", "n", "false", "off", "0"]:
            return False
    raise TypeError(f"Cannot interpret as boolean: `{arg}`")


def process_glob_list_arg(arg):
    """Convert a list of glob patterns or filenames into a list of files
    The initial list can take the form of a comma-separated string or
    a proper list. Order is preserved, but duplicates will be removed.

    Note: this function processes glob patterns, but doesn't validate
    that the files actually exist. For example, if the pattern is
    'foo.bar' and there is no file named 'foo.bar', the literal string
    'foo.bar' will be included in the returned files.

    Similarly, if the pattern is '*.baz' and it doesn't match any files,
    the literal string '*.baz' will be returned.
    """
    initial_list = process_list_arg(arg)

    if not arg:
        return []

    files = []
    for path in initial_list:
        more_files = glob.glob(path, recursive=True)
        if len(more_files):
            files += sorted(more_files)
        else:
            files.append(path)
    # In python 3.6+ dict is ordered, so we'll use it to weed
    # out duplicates. We can't use a set because sets aren't ordered.
    return list(dict.fromkeys(files))


def process_list_arg(arg):
    """Parse a string into a list separated by commas with whitespace stripped"""
    if isinstance(arg, list):
        return arg
    elif isinstance(arg, str):
        args = []
        for part in arg.split(","):
            args.append(part.strip())
        return args


def process_list_of_pairs_dict_arg(arg):
    """Process an arg in the format "aa:bb,cc:dd" """
    if isinstance(arg, dict):
        return arg
    elif isinstance(arg, str):
        rc = {}
        for key_value in arg.split(","):
            subparts = key_value.split(":", 1)
            if len(subparts) == 2:
                key, value = subparts
                if key in rc:
                    raise TaskOptionsError(f"Var specified twice: {key}")
                rc[key] = value
            else:
                raise TaskOptionsError(f"Var is not a name/value pair: {key_value}")
        return rc
    else:
        raise TaskOptionsError(f"Arg is not a dict or string ({type(arg)}): {arg}")


def decode_to_unicode(content):
    """decode ISO-8859-1 to unicode, when using sf api"""
    if content and not isinstance(content, str):
        try:
            # Try to decode ISO-8859-1 to unicode
            return content.decode("ISO-8859-1")
        except UnicodeEncodeError:
            # Assume content is unicode already
            return content
    return content


def merge_config(configs):
    """recursively deep-merge the configs into one another (highest priority comes first)"""
    new_config = {}

    for name, config in configs.items():
        new_config = dictmerge(new_config, config, name)

    return new_config


def dictmerge(a, b, name=None):
    """Deeply merge two ``dict``s that consist of lists, dicts, and scalars.
    This function (recursively) merges ``b`` INTO ``a``, does not copy any values, and returns ``a``.

    based on https://stackoverflow.com/a/15836901/5042831
    NOTE: tuples and arbitrary objects are NOT handled and will raise TypeError"""

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
                        a[key] = copy.deepcopy(b[key])
            else:
                raise TypeError(
                    f'Cannot merge non-dict of type "{type(b)}" into dict "{a}"'
                )
        else:
            raise TypeError(
                f'dictmerge does not supporting merging "{type(b)}" into "{type(a)}"'
            )
    except TypeError as e:
        raise ConfigMergeError(
            f'TypeError "{e}" in key "{key}" when merging "{type(b)}" into "{type(a)}"',
            config_name=name,
        )
    return a


def format_duration(duration: timedelta):
    hours, remainder = divmod(duration.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    hours = f"{int(hours)}h:" if hours > 0 else ""
    minutes = f"{int(minutes)}m:" if (hours or minutes) else ""
    seconds = f"{str(int(seconds))}s"
    return hours + minutes + seconds

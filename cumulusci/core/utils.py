""" Utilities for CumulusCI Core

import_global: task class defn import helper
process_bool_arg: determine true/false for a commandline arg
decode_to_unicode: get unicode string from sf api """

from datetime import datetime
import copy
import glob
import pytz
import time
from shutil import rmtree
from typing import Union
import warnings

from cumulusci.core.exceptions import (
    ConfigMergeError,
    CumulusCIException,
    TaskOptionsError,
)


def import_global(path):
    """ Import a class from a string module class path """
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


def process_bool_arg(arg: Union[int, str, None]):
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
    """ Parse a string into a list separated by commas with whitespace stripped """
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
            subparts = key_value.split(":")
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
    """ decode ISO-8859-1 to unicode, when using sf api """
    if content and not isinstance(content, str):
        try:
            # Try to decode ISO-8859-1 to unicode
            return content.decode("ISO-8859-1")
        except UnicodeEncodeError:
            # Assume content is unicode already
            return content
    return content


def merge_config(configs):
    """ recursively deep-merge the configs into one another (highest priority comes first) """
    new_config = {}

    for name, config in configs.items():
        new_config = dictmerge(new_config, config, name)

    return new_config


def dictmerge(a, b, name=None, prefix=None):
    """Deeply merge two ``dict``s that consist of lists, dicts, and scalars.
    This function (recursively) merges ``b`` INTO ``a``, does not copy any values, and returns ``a``.

    prefix: will append
    based on https://stackoverflow.com/a/15836901/5042831
    NOTE: tuples and arbitrary objects are NOT handled and will raise TypeError"""

    key = None
    has_prefix = False
    if b is None:
        return a

    try:
        if a is None or isinstance(a, (bytes, int, str, float)):
            if prefix and (
                (isinstance(b, str) and not b.startswith(f"{prefix} "))
                or not isinstance(b, str)
            ):
                b = f"{prefix} {b}"
            # first run, or if ``a``` is a scalar
            a = b
        elif isinstance(a, list):
            # lists can be only appended
            if isinstance(b, list):
                if prefix and not any(
                    [i.startswith(f"{prefix} ") for i in b if isinstance(i, str)]
                ):
                    b = [f"{prefix} {str(i)}" for i in b]
                # merge lists
                a.extend(b)
            else:
                if prefix:
                    b = f"{prefix} {b}"
                # append to list
                a.append(b)
        elif isinstance(a, dict):
            # dicts must be merged
            if isinstance(b, dict):
                for key in b:
                    if key in a:
                        a[key] = dictmerge(a[key], b[key], name, prefix)
                    else:
                        if prefix and not has_prefix:
                            b = prefix_dict_values(b, prefix)
                            has_prefix = True
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


def prefix_dict_values(d, prefix, new=None):
    """
    Recursively traverse d and convert all values to strings and prefix them with: '{prefix} '.

    Returns
        A new dictionary with prefixed values.

    Raises
        CumulusCIException when an unsupported type is encountered
    """
    if d is None:
        return None

    if new is None:
        new = {}

    for key in d:
        v = d[key]
        if isinstance(v, (bytes, int, str, float)):
            new[key] = f"{prefix} {v}"
        elif isinstance(v, list):
            new[key] = [f"{prefix} {i}" for i in v]
        elif isinstance(v, dict):
            new[key] = {}
            new[key] = prefix_dict_values(v, prefix, new=new[key])
        elif v is not None:
            raise CumulusCIException(
                f"Found unsupported type <{type(v)}> parsing dictionary."
            )

    return new


def get_sub_dicts(keys, dicts):
    """
    Attempts set each dict in dicts equal to the subdict located
    at dict[key[i]][key[i+1]]... The length of the keys list correlates to
    the depth of the subdictionary to retrieve.

    If no sub-dict exists in the given dict, then set that dict to None.

    For example, if `keys == ['tasks','execute_anon']` then this function
    attempts to set each dict in the list to whatever is under `dicts['tasks']['execute_anon']`
    for each dict in the list.

    Argument
        param1 - list of strings that represent keys at specific levels of a dicitonary.
        param2 - list of dicts to filter based on the given keys.

    Returns
        The filtered list of dicts
    """
    if not keys:
        return dicts

    for i in range(len(dicts)):
        if not dicts[i]:
            dicts[i] = None
            continue
        for key in keys:
            try:
                if dicts[i]:
                    dicts[i] = dicts[i][key]
            except KeyError:
                dicts[i] = None

    return dicts


def cleanup_org_cache_dirs(keychain, project_config):
    """Cleanup directories that are not associated with a connected/live org."""

    if not project_config or not project_config.cache_dir:
        return
    domains = set()
    for org in keychain.list_orgs():
        org_config = keychain.get_org(org)
        domain = org_config.get_domain()
        if domain:
            domains.add(domain)

    assert project_config.cache_dir
    assert keychain.global_config_dir

    project_org_directories = (project_config.cache_dir / "orginfo").glob("*")
    global_org_directories = (keychain.global_config_dir / "orginfo").glob("*")

    for directory in list(project_org_directories) + list(global_org_directories):
        if directory.name not in domains:
            rmtree(directory)

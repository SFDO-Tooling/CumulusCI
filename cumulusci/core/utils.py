""" Utilities for CumulusCI Core"""

import copy
import glob
import json
import time
import typing as T
import warnings
from datetime import datetime, timedelta
from logging import getLogger
from pathlib import Path

import pytz

from cumulusci.core.exceptions import (
    ConfigMergeError,
    CumulusCIException,
    TaskOptionsError,
)


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
    if isinstance(arg, Path):
        arg = str(arg)

    if isinstance(arg, list):
        return arg
    elif isinstance(arg, str):
        args = []
        for part in arg.split(","):
            args.append(part.strip())
        return args
    elif arg is None:
        # backwards compatible behaviour.
        return None
    else:
        getLogger(__file__).warn(
            f"Unknown option type `{type(arg)}` for value `{arg}`."
            "This will be an error in a future version of CCI."
        )


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
    """
    First remove any flow steps that are being overridden so that there are no conflicts
    or different step types after merging. Then recursively deep-merge the configs into
    one another (highest priority comes first)
    """
    config_copies = {name: copy.deepcopy(config) for name, config in configs.items()}
    cleaned_configs = cleanup_flow_step_override_conflicts(config_copies)

    new_config = {}
    for name, config in cleaned_configs.items():
        new_config = dictmerge(new_config, config, name)

    return new_config


def cleanup_flow_step_override_conflicts(configs: T.List[dict]) -> T.List[dict]:
    """
    If a flow step is been overridden with a step of a different type (i.e. tas, flow),
    then we need to set the step that is _lower_ in precedence order to an empty dict ({}).
    If we don't, then we will end up with both "flow" and "task" listed in the step_config which
    leads to an error when CumulusCI attempts to run that step in the flow.

    We need to also account for scenarios where a single flow step
    is being overriden more than once.

    Example:
    A flow step in the universal config is being overridden somewhere
    in the project_config, which is being overridden by additional_yaml.

    The while loop below is how we account for these scenarios.
    """
    config_precedence_order = [
        "additional_yaml",
        "project_local_config",
        "project_config",
        "global_config",
        "universal_config",
    ]
    while len(config_precedence_order) > 1:
        overriding_config = config_precedence_order[0]
        config_precedence_order = config_precedence_order[1:]
        for config_to_override in config_precedence_order:
            if configs_present_and_not_empty(
                [config_to_override, overriding_config], configs
            ):
                remove_overridden_flow_steps_in_config(
                    configs[config_to_override], configs[overriding_config]
                )

    return configs


def configs_present_and_not_empty(
    configs_to_check: T.List[dict], configs: dict
) -> bool:
    return all(c in configs and c != {} for c in configs_to_check)


def remove_overridden_flow_steps_in_config(
    config_to_override: dict, overriding_config: dict
):
    """If any steps of flows from the config_to_override are being overridden in overriding_config,
    then we need to set those steps in the config_to_override to an empty dict so that we don't have
    both a "task" and a "flow" listed in a flow step after merging the configs with `dictmerge()`."""

    if "flows" not in config_to_override or "flows" not in overriding_config:
        return

    for flow, flow_config in overriding_config["flows"].items():
        for (
            step_num,
            overriding_step_config,
        ) in flow_config.get("steps", {}).items():
            cleanup_old_flow_step_replace_syntax(overriding_step_config)
            both_configs_have_flow_and_step = config_has_flow_and_step_num(
                config_to_override, flow, step_num
            )
            if both_configs_have_flow_and_step:
                step_config_to_override = config_to_override["flows"][flow]["steps"][
                    step_num
                ]
                steps_same_type = steps_are_same_type(
                    overriding_step_config, step_config_to_override
                )

                link_missing_task_or_flow(
                    step_config_to_override, overriding_step_config
                )

                if not steps_same_type:
                    config_to_override["flows"][flow]["steps"][step_num] = {}


def link_missing_task_or_flow(
    step_config_to_override: dict, overriding_step_config: dict
):
    """If the incoming override does not have task/flow defined then inherit from
    the flow step that we're overridding."""
    if "flow" not in overriding_step_config and "task" not in overriding_step_config:
        if "task" in step_config_to_override:
            overriding_step_config["task"] = step_config_to_override["task"]
        elif "flow" in step_config_to_override:
            overriding_step_config["flow"] = step_config_to_override["flow"]


def cleanup_old_flow_step_replace_syntax(step_config: dict):
    """When replacing flow steps with a step of a different type, the old syntax
    had users declare the original step type as 'None' along with the new step type.
    If both are present, we want to remove the one that has a value of 'None'."""
    if all(s_type in step_config for s_type in ("task", "flow")):
        if step_config["flow"] == "None" and step_config["task"] == "None":
            raise CumulusCIException(
                "Cannot have both step types declared with a value of 'None'."
                "For information on replacing a flow step see: https://cumulusci.readthedocs.io/en/latest/config.html#replace-a-flow-step"
            )
        elif step_config["flow"] == "None":
            del step_config["flow"]
        else:
            del step_config["task"]


def config_has_flow_and_step_num(config: dict, flow_name: str, step_num: int) -> bool:
    return (
        flow_name in config["flows"] and step_num in config["flows"][flow_name]["steps"]
    )


def steps_are_same_type(step_one_config: dict, step_two_config: dict) -> bool:
    """If both steps are of the same type returns True, else False."""
    config_one_type = "task" if "task" in step_one_config else "flow"
    config_two_type = "task" if "task" in step_two_config else "flow"

    return config_one_type == config_two_type


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


def make_jsonable(x):
    """Attempts to json serialize an object.
    If it is not serializable,
    returns a list if it's a set
    or a string representation for anything else.
    """
    if isinstance(x, set):
        return list(x)
    try:
        json.dumps(x)
        return x
    except (TypeError, OverflowError):
        return str(x)

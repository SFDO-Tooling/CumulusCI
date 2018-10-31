""" Utilities for CumulusCI Core

import_class: task class defn import helper
process_bool_arg: determine true/false for a commandline arg
decode_to_unicode: get unicode string from sf api """
from __future__ import unicode_literals

from builtins import bytes, int, str


from past.builtins import basestring
from future.utils import native_str

from datetime import datetime
import pytz
import time
import yaml
from collections import OrderedDict

from cumulusci.core.exceptions import ConfigMergeError


def import_class(path):
    """ Import a class from a string module class path """
    components = path.split(".")
    module = components[:-1]
    module = ".".join(module)
    mod = __import__(module, fromlist=[native_str(components[-1])])
    return getattr(mod, native_str(components[-1]))


def parse_datetime(dt_str, format):
    """Create a timezone-aware datetime object from a datetime string."""
    t = time.strptime(dt_str, format)
    return datetime(t[0], t[1], t[2], t[3], t[4], t[5], t[6], pytz.UTC)


def process_bool_arg(arg):
    """ Determine True/False from argument """
    if isinstance(arg, bool):
        return arg
    elif isinstance(arg, basestring):
        if arg.lower() in ["true", "1"]:
            return True
        elif arg.lower() in ["false", "0"]:
            return False


def process_list_arg(arg):
    """ Parse a string into a list separated by commas with whitespace stripped """
    if isinstance(arg, list):
        return arg
    elif isinstance(arg, basestring):
        args = []
        for part in arg.split(","):
            args.append(part.strip())
        return args


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


class OrderedLoader(yaml.SafeLoader):
    def _construct_dict_mapping(self, node):
        self.flatten_mapping(node)
        return OrderedDict(self.construct_pairs(node))


OrderedLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    OrderedLoader._construct_dict_mapping,
)


def ordered_yaml_load(stream,):
    """ Load YAML file with OrderedDict, needed for Py2 
    
    code adapted from: https://stackoverflow.com/a/21912744/5042831"""

    return yaml.load(stream, OrderedLoader)


def merge_config(configs):
    """ recursively deep-merge the configs into one another (highest priority comes first) """
    new_config = {}

    for name, config in configs.items():
        new_config = dictmerge(new_config, config, name)

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

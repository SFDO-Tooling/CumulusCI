""" Utilities for CumulusCI Core

import_class: task class defn import helper
process_bool_arg: determine true/false for a commandline arg
decode_to_unicode: get unicode string from sf api """
from __future__ import unicode_literals

from past.builtins import basestring
def import_class(path):
    """ Import a class from a string module class path """
    components = path.split('.')
    module = components[:-1]
    module = '.'.join(module)
    # __import__ needs a native str() on py2
    mod = __import__(module, fromlist=[str(components[-1])])
    return getattr(mod, str(components[-1]))


def process_bool_arg(arg):
    """ Determine True/False from argument """
    if isinstance(arg, bool):
        return arg
    elif isinstance(arg, basestring):
        if arg.lower() in ['true', '1']:
            return True
        elif arg.lower() in ['false', '0']:
            return False


def decode_to_unicode(content):
    """ decode ISO-8859-1 to unicode, when using sf api """
    if content:
        try:
            # Try to decode ISO-8859-1 to unicode
            return content.decode('ISO-8859-1')
        except UnicodeEncodeError:
            # Assume content is unicode already
            return content

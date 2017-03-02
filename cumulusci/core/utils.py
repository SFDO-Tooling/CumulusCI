""" Utilities for CumulusCI Core

import_class: Task class defn import helper """

import logging


def import_class(path):
    """ Import a class from a string module class path """
    components = path.split('.')
    module = components[:-1]
    module = '.'.join(module)
    mod = __import__(module, fromlist=[components[-1]])
    return getattr(mod, components[-1])

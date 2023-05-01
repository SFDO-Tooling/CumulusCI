import os
import sys

from simple_salesforce import api, bulk

from cumulusci.__about__ import __version__

__import__("pkg_resources").declare_namespace("cumulusci")

__location__ = os.path.dirname(os.path.realpath(__file__))

__version__ = __version__

if sys.version_info < (3, 8):  # pragma: no cover
    raise Exception("CumulusCI requires Python 3.8+.")

api.OrderedDict = dict
bulk.OrderedDict = dict

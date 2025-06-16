import os
import sys
from importlib.metadata import PackageNotFoundError, version

from simple_salesforce import api, bulk

__location__ = os.path.dirname(os.path.realpath(__file__))

try:
    __version__ = version("cumulusci")
except PackageNotFoundError:
    __version__ = "unknown"

if sys.version_info < (3, 8):  # pragma: no cover
    raise Exception("CumulusCI requires Python 3.8+.")

api.OrderedDict = dict
bulk.OrderedDict = dict

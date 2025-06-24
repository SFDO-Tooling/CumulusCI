import os
import sys
import warnings
from importlib.metadata import PackageNotFoundError, version

# Suppress pkg_resources deprecation warnings from dependencies
warnings.filterwarnings("ignore", message=".*pkg_resources.*", category=UserWarning)

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

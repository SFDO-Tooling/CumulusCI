import os
import sys
import warnings

# Suppress pkg_resources deprecation warning from PyFilesystem (fs) package
# See: https://github.com/PyFilesystem/pyfilesystem2/issues/577
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
)

from simple_salesforce import api, bulk

__location__ = os.path.dirname(os.path.realpath(__file__))

from .__about__ import __version__

if sys.version_info < (3, 11):  # pragma: no cover
    raise Exception("Clariti CumulusCI requires Python 3.11+.")

api.OrderedDict = dict
bulk.OrderedDict = dict

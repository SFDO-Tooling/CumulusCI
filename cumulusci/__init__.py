import os
import sys

from simple_salesforce import api, bulk

# For tasks that don't connect to orgs but do nevertheless need
# to look at the API version (e.g. to write it during freezing
# or XML rewriting)
DEFAULT_SF_API_VERSION = "56.0"

__import__("pkg_resources").declare_namespace("cumulusci")

__location__ = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(__location__, "version.txt")) as f:
    __version__ = f.read().strip()

if sys.version_info < (3, 8):  # pragma: no cover
    raise Exception("CumulusCI requires Python 3.8+.")

api.OrderedDict = dict
bulk.OrderedDict = dict

import os
import sys

from simple_salesforce import api, bulk

__import__("pkg_resources").declare_namespace("cumulusci")

__location__ = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(__location__, "version.txt")) as f:
    __version__ = f.read().strip()

if sys.version_info < (3, 8):  # pragma: no cover
    raise Exception("CumulusCI requires Python 3.8+.")

api.OrderedDict = dict
bulk.OrderedDict = dict

from cumulusci.utils.http.requests_utils import init_requests_trust

# Should we do this only when cci is being run as a CLI and not imported as a library?
init_requests_trust()

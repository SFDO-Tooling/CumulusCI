import os
import sys

__version__ = "3.0.2"

__location__ = os.path.dirname(os.path.realpath(__file__))

if sys.version_info < (3, 6):
    raise Exception("CumulusCI requires Python 3.6+.")

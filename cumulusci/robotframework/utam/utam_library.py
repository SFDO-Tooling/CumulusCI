from robot.libraries.BuiltIn import BuiltIn
from robot.api.deco import keyword
from pathlib import Path
import os


class UTAMLibrary:
    def __init__(self, *names, paths=[]):
        for name in names:
            self.import_utam(name)
        here = Path(__file__).parent
        os.environ["UTAMPATH"] = ":".join([str(here / "resources")])

    @keyword(tags=["utam"])
    def import_utam(self, *names):
        """Create one or more UTAM page objects from their json definition"""
        for name in names:
            BuiltIn().import_library(
                "cumulusci.robotframework.utam.UTAM", name, "WITH NAME", f"UTAM:{name}"
            )

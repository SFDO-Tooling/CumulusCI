from robot.libraries.BuiltIn import BuiltIn


class BaseLibrary:
    """A base class for salesforce keyword libraries"""

    @property
    def builtin(self):
        return BuiltIn()

    @property
    def selenium(self):
        return self.builtin.get_library_instance("SeleniumLibrary")

    @property
    def cumulusci(self):
        return self.builtin.get_library_instance("CumulusCI")

from robot.libraries.BuiltIn import BuiltIn


class BaseLibrary:
    def __init__(self):
        self._builtin = None
        self._cumulusci = None
        self._salesforce_api = None
        self._salesforce = None

    @property
    def salesforce(self):
        if getattr(self, "_salesforce", None) is None:
            self._salesforce = self.builtin.get_library_instance(
                "cumulusci.robotframework.Salesforce"
            )
        return self._salesforce

    @property
    def salesforce_api(self):
        if getattr(self, "_salesforce_api", None) is None:
            self._salesforce_api = self.builtin.get_library_instance(
                "cumulusci.robotframework.SalesforceAPI"
            )
        return self._salesforce_api

    @property
    def builtin(self):
        if getattr(self, "_builtin", None) is None:
            self._builtin = BuiltIn()
        return self._builtin

    @property
    def cumulusci(self):
        if getattr(self, "_cumulusci", None) is None:
            self._cumulusci = self.builtin.get_library_instance(
                "cumulusci.robotframework.CumulusCI"
            )
        return self._cumulusci

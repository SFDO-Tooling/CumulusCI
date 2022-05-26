from robot.libraries.BuiltIn import BuiltIn


class BaseLibrary:
    def __init__(self):
        self._builtin = None
        self._cumulusci = None
        self._salesforce_api = None
        self._salesforce = None

    @property
    def salesforce(self):
        if self._salesforce is None:
            self._salesforce = self.builtin.get_library_instance(
                "cumulusci.robotframework.Salesforce"
            )
        return self._salesforce

    @property
    def salesforce_api(self):
        if self._salesforce_api is None:
            self._salesforce_api = self.builtin.get_library_instance(
                "cumulusci.robotframework.SalesforceAPI"
            )
        return self._salesforce_api

    @property
    def builtin(self):
        if self._builtin is None:
            self._builtin = BuiltIn()
        return self._builtin

    @property
    def cumulusci(self):
        if self._cumulusci is None:
            self._cumulusci = self.builtin.get_library_instance(
                "cumulusci.robotframework.CumulusCI"
            )
        return self._cumulusci

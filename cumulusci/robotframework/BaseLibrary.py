import logging
from robot.libraries.BuiltIn import BuiltIn, RobotNotRunningError
from cumulusci.robotframework.utils import RetryingSeleniumLibraryMixin


class BaseLibrary(RetryingSeleniumLibraryMixin):
    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self, debug=False):
        self.debug = debug
        self.retry_selenium = True
        # Turn off info logging of all http requests
        logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(
            logging.WARN
        )

    @property
    def salesforce_api_version(self):
        try:
            client = self.cumulusci.tooling
            response = client._call_salesforce(
                "GET", "https://{}/services/data".format(client.sf_instance)
            )
            latest_api_version = float(response.json()[-1]["version"])
            return latest_api_version

        except RobotNotRunningError:
            # not sure if this should return None, a reasonable default value,
            # or raise an exception. :-\
            return None

    @property
    def builtin(self):
        return BuiltIn()

    @property
    def cumulusci(self):
        return self.builtin.get_library_instance("cumulusci.robotframework.CumulusCI")

    @property
    def salesforce(self):
        return self.builtin.get_library_instance("cumulusci.robotframework.Salesforce")

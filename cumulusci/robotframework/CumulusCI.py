import logging

from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn

from cumulusci.cli.runtime import CliRuntime
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import CURRENT_TASK
from cumulusci.core.utils import import_global
from cumulusci.robotframework.utils import set_pdb_trace
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.tasks.robotframework.robotframework import Robot


class CumulusCI(object):
    """ Library for accessing CumulusCI for the local git project

        This library allows Robot Framework tests to access credentials to a
        Salesforce org created by CumulusCI, including Scratch Orgs.  It also
        exposes the core logic of CumulusCI including interactions with the
        Salesforce API's and project specific configuration including custom
        and customized tasks and flows.

        Initialization requires a single argument, the org name for the target
        CumulusCI org.  If running your tests via cci's robot task (recommended),
        you can initialize the library in your tests taking advantage of the
        variable set by the robot task:
        | ``*** Settings ***``
        |
        | Library  cumulusci.robotframework.CumulusCI  ${ORG}

    """

    ROBOT_LIBRARY_SCOPE = "GLOBAL"

    def __init__(self, org_name=None):
        if not org_name:
            org_name = "dev"
        self.org_name = org_name
        self._project_config = None
        self._org = None

        # Turn off info logging of all http requests
        logging.getLogger("requests.packages.urllib3.connectionpool").setLevel(
            logging.WARN
        )

    @property
    def project_config(self):
        if self._project_config is None:
            if CURRENT_TASK.stack and isinstance(CURRENT_TASK.stack[0], Robot):
                # If CumulusCI is running a task, use that task's config
                return CURRENT_TASK.stack[0].project_config
            else:
                logger.console("Initializing CumulusCI config\n")
                self._project_config = CliRuntime().project_config
        return self._project_config

    def set_project_config(self, project_config):
        logger.console("\n")
        self._project_config = project_config

    @property
    def keychain(self):
        return self.project_config.keychain

    @property
    def org(self):
        if self._org is None:
            if CURRENT_TASK.stack and isinstance(CURRENT_TASK.stack[0], Robot):
                # If CumulusCI is running a task, use that task's org
                return CURRENT_TASK.stack[0].org_config
            else:
                self._org = self.keychain.get_org(self.org_name)
        return self._org

    @property
    def sf(self):
        return self._init_api()

    @property
    def tooling(self):
        return self._init_api("tooling/")

    def set_login_url(self):
        """ Sets the LOGIN_URL variable in the suite scope which will
            automatically log into the target Salesforce org.

            Typically, this is run during Suite Setup
        """
        BuiltIn().set_suite_variable("${LOGIN_URL}", self.org.start_url)

    def get_org_info(self):
        """ Returns a dictionary of the org information for the current target
            Salesforce org
        """
        return self.org.config

    def login_url(self, org=None):
        """ Returns the login url which will automatically log into the target
            Salesforce org.  By default, the org_name passed to the library
            constructor is used but this can be overridden with the org option
            to log into a different org.
        """
        if org is None:
            org = self.org
        else:
            org = self.keychain.get_org(org)
        return org.start_url

    def get_community_info(self, community_name, key=None, force_refresh=False):
        """This keyword uses the Salesforce API to get information about a community.

        This keyword requires the exact community name as its first argumment.

        - If no key is given, all of the information returned by the API will be
          returned by this keyword in the form of a dictionary
        - If a key is given, only the value for that key will be returned.

        Some of the supported keys include name, siteUrl, and
        loginUrl. For a comprehensive list see the
        [https://developer.salesforce.com/docs/atlas.en-us.chatterapi.meta/chatterapi/connect_responses_community.htm|API documentation],
        or call this keyword without the key argument and examine the
        results.

        An API call will be made the first time this keyword is used, and
        the return values will be cached. Subsequent calls will not call
        the API unless the requested community name is not in the cached
        results, or unless the force_refresh parameter is set to True.
        """
        community_info = self.org.get_community_info(
            community_name, force_refresh=force_refresh
        )
        if key is None:
            return community_info
        else:
            if key not in community_info:
                raise Exception("Invalid key '{}'".format(key))
            return community_info[key]

    def get_namespace_prefix(self, package=None):
        """ Returns the namespace prefix (including __) for the specified package name.
        (Defaults to project__package__name_managed from the current project config.)

        Returns an empty string if the package is not installed as a managed package.
        """
        result = ""
        if package is None:
            package = self.project_config.project__package__name_managed
        packages = self.tooling.query(
            "SELECT SubscriberPackage.NamespacePrefix, SubscriberPackage.Name "
            "FROM InstalledSubscriberPackage"
        )
        match = [
            p for p in packages["records"] if p["SubscriberPackage"]["Name"] == package
        ]
        if match:
            result = match[0]["SubscriberPackage"]["NamespacePrefix"] + "__"
        return result

    def run_task(self, task_name, **options):
        """ Runs a named CumulusCI task for the current project with optional
            support for overriding task options via kwargs.

            Examples:
            | =Keyword= | =task_name= | =task_options=             | =comment=                        |
            | Run Task  | deploy      |                            | Run deploy with standard options |
            | Run Task  | deploy      | path=path/to/some/metadata | Run deploy with custom path      |
        """
        task_config = self.project_config.get_task(task_name)
        class_path = task_config.class_path
        logger.console("\n")
        task_class, task_config = self._init_task(class_path, options, task_config)
        return self._run_task(task_class, task_config)

    def run_task_class(self, class_path, **options):
        """ Runs a CumulusCI task class with task options via kwargs.

            Use this keyword to run logic from CumulusCI tasks which have not
            been configured in the project's cumulusci.yml file.  This is
            most useful in cases where a test needs to use task logic for
            logic unique to the test and thus not worth making into a named
            task for the project

            Examples:
            | =Keyword=      | =task_class=                     | =task_options=                            |
            | Run Task Class | cumulusci.task.utils.DownloadZip | url=http://test.com/test.zip dir=test_zip |
        """
        logger.console("\n")
        task_class, task_config = self._init_task(class_path, options, TaskConfig())
        return self._run_task(task_class, task_config)

    def _init_api(self, base_url=None):
        client = get_simple_salesforce_connection(self.project_config, self.org)
        if base_url is not None:
            client.base_url += base_url
        return client

    def _init_task(self, class_path, options, task_config):
        task_class = import_global(class_path)
        task_config = self._parse_task_options(options, task_class, task_config)
        return task_class, task_config

    def _parse_task_options(self, options, task_class, task_config):
        if "options" not in task_config.config:
            task_config.config["options"] = {}
        # Parse options and add to task config
        if options:
            for name, value in options.items():
                # Validate the option
                if name not in task_class.task_options:
                    raise TaskOptionsError(
                        'Option "{}" is not available for task {}'.format(
                            name, task_class
                        )
                    )

                # Override the option in the task config
                task_config.config["options"][name] = value

        return task_config

    def _run_task(self, task_class, task_config):
        task = task_class(self.project_config, task_config, org_config=self.org)

        task()
        return task.return_values

    def debug(self):
        """Pauses execution and enters the Python debugger."""
        set_pdb_trace()

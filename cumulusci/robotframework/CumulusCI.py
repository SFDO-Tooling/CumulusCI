import logging

import robot.api.logger
from robot.libraries.BuiltIn import BuiltIn

from cumulusci.cli.runtime import CliRuntime
from cumulusci.core.config import ScratchOrgConfig, TaskConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import CURRENT_TASK
from cumulusci.core.utils import import_global
from cumulusci.robotframework.utils import set_pdb_trace
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.tasks.robotframework.robotframework import Robot


class CumulusCI(object):
    """Library for accessing CumulusCI for the local git project

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
            if getattr(CURRENT_TASK, "stack", None) and isinstance(
                CURRENT_TASK.stack[0], Robot
            ):
                # If CumulusCI is running a task, use that task's config
                return CURRENT_TASK.stack[0].project_config
            else:
                robot.api.logger.console("Initializing CumulusCI config\n")
                self._project_config = CliRuntime().project_config
        return self._project_config

    def set_project_config(self, project_config):
        self._project_config = project_config

    @property
    def keychain(self):
        return self.project_config.keychain

    @property
    def org(self):
        if self._org is None:
            if getattr(CURRENT_TASK, "stack", None) and isinstance(
                CURRENT_TASK.stack[0], Robot
            ):
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
        """Sets the LOGIN_URL variable in the suite scope which will
        automatically log into the target Salesforce org.

        Typically, this is run during Suite Setup
        """
        BuiltIn().set_suite_variable("${LOGIN_URL}", self.org.start_url)

    def get_org_info(self):
        """Returns a dictionary of the org information for the current target
        Salesforce org
        """
        return self.org.config

    def login_url(self, org=None, **userfields):
        """Returns the login url which will automatically log into the target
        Salesforce org.  By default, the org_name passed to the library
        constructor is used but this can be overridden with the org option
        to log into a different org.

        If userfields are provided, the username and access token
        for the given user will be used. If not provided, the access token
        for the org's default user will be used.

        The userfields argument is largely useful for scratch orgs, but can
        also work with connected persistent orgs if you've connected the org
        with the given username.

        Example:

        | ${login url}=  Login URL  alias=dadvisor

        """
        org = self.org if org is None else self.keychain.get_org(org)

        if userfields:
            if org.get_access_token is not None:
                # connected persistent org configs won't have the get_access_token method
                access_token = org.get_access_token(**userfields)
            else:
                access_token = self._find_access_token(org, **userfields)
            login_url = f"{org.instance_url}/secur/frontdoor.jsp?sid={access_token}"
            return login_url
        else:
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
        """Returns the namespace prefix (including __) for the specified package name.
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
        """Runs a named CumulusCI task for the current project with optional
        support for overriding task options via kwargs.

        Note: task_name can be prefixed with the name of another project,
        just the same as when running the task from the command line. The other
        project needs to have been defined in the 'sources' section of cumulusci.yml.

        The task output will appear in the robot log.

        Examples:
        | =Keyword= | =task_name= | =task_options=             | =comment=                        |
        | Run Task  | deploy      |                            | Run deploy with standard options |
        | Run Task  | deploy      | path=path/to/some/metadata | Run deploy with custom path      |
        | Run task  | npsp:deploy_rd2_config  |                | Run the deploy_rd2_config task from the NPSP project |
        """
        task_config = self.project_config.get_task(task_name)
        class_path = task_config.class_path
        task = self._init_task(class_path, options, task_config)
        return self._run_task(task)

    def run_task_class(self, class_path, **options):
        """Runs a CumulusCI task class with task options via kwargs.

        Use this keyword to run logic from CumulusCI tasks which have not
        been configured in the project's cumulusci.yml file.  This is
        most useful in cases where a test needs to use task logic for
        logic unique to the test and thus not worth making into a named
        task for the project

        The task output will appear in the robot log.

        Examples:
        | =Keyword=      | =task_class=                     | =task_options=                            |
        | Run Task Class | cumulusci.task.utils.DownloadZip | url=http://test.com/test.zip dir=test_zip |
        """
        task = self._init_task(class_path, options, TaskConfig())
        return self._run_task(task)

    def _init_api(self, base_url=None):
        client = get_simple_salesforce_connection(self.project_config, self.org)
        if base_url is not None:
            client.base_url += base_url
        return client

    def _init_task(self, class_path, options, task_config):
        task_class = import_global(class_path)
        task_config = self._parse_task_options(options, task_class, task_config)
        # Python deprecated the logger method "warn" in favor of
        # "warning". Robot didn't get the memo and only has a "warn"
        # method. Some tasks use "warning", so this makes sure the
        # robot logger can handle that.
        if not hasattr(robot.api.logger, "warning"):
            robot.api.logger.warning = robot.api.logger.warn

        # robot's logger doesn't have the 'log' method, and there's at least one
        # piece of code that depends on this method. So, if we haven't already
        # monkeypatched it in, do so now.  See W-10503175
        if not hasattr(robot.api.logger, "log"):
            robot.api.logger.log = _logger_log

        task = task_class(
            task_config.project_config or self.project_config,
            task_config,
            org_config=self.org,
            logger=robot.api.logger,
        )
        return task

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

    def _run_task(self, task):
        task()
        return task.return_values

    def _find_access_token(self, base_org, **userfields):
        """Search connected orgs for a user and return the access token

        The org config for connected orgs doesn't have an access token
        for each user. Instead, we have an access token for the org as
        a whole. This searches all connected org configs for an org
        with the given user (either by username or alias) and returns
        the access token for the org.

        It is expected that userfields contains either a 'username'
        or 'alias' field. If a username is provided, that's what will
        be used. If not, this function will do a query to find a username
        that matches the given parameters.

        """

        username = userfields.get("username", None)
        if username is None:
            where = [f"{key}='{value}'" for key, value in userfields.items()]
            query = f"SELECT Username FROM User WHERE {' AND '.join(where)}"
            result = base_org.salesforce_client.query(query).get("records", [])
            if len(result) == 0:
                query = ", ".join(where)
                raise Exception(
                    f"Couldn't find a username in org {base_org.name} for the specified user ({query})."
                )
            elif len(result) > 1:
                results = ", ".join([user["Username"] for user in result])
                raise Exception(
                    f"More than one user matched the search critiera for org {base_org.name} ({results})."
                )
            else:
                username = result[0]["Username"]

        for org_name in self.keychain.list_orgs():
            org = self.keychain.get_org(org_name)
            if not isinstance(org, ScratchOrgConfig):
                if "userinfo" in org.config:
                    if org.config["userinfo"]["preferred_username"] == username:
                        return org.access_token
        return None

    def debug(self):
        """Pauses execution and enters the Python debugger."""
        set_pdb_trace()


def _logger_log(level, msg):
    """Implements the 'log' method for robot.api.logger

    This takes a normal python log level, converts it to one of
    the supported robot log levels, then calls the write method
    of the logger.
    """
    level = (
        "ERROR"
        if level >= logging.ERROR
        else "WARN"
        if level >= logging.WARN
        else "INFO"
        if level >= logging.INFO
        else "DEBUG"
    )
    robot.api.logger.write(msg, level)

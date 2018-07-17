import logging
from cumulusci.cli.config import CliConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import CURRENT_TASK
from cumulusci.core.utils import import_class
from cumulusci.tasks.robotframework.robotframework import Robot
from robot.api import logger
from robot.libraries.BuiltIn import BuiltIn
from simple_salesforce import Salesforce

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
            org_name = 'dev'
        self.org_name = org_name
        self._project_config = None
        self._org = None
        self._sf = None
        self._tooling = None
        # Turn off info logging of all http requests 
        logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARN)

    @property
    def project_config(self):
        if self._project_config is None:
            if CURRENT_TASK and isinstance(CURRENT_TASK, Robot):
                # If CumulusCI is running a task, use that task's config
                return CURRENT_TASK.project_config
            else:
                logger.console('Initializing CumulusCI config\n')
                self._project_config = CliConfig().project_config
        return self._project_config

    def set_project_config(self, project_config):
        logger.console('\n')
        self._project_config = project_config
    
    @property
    def keychain(self):
        return self.project_config.keychain

    @property
    def org(self):
        if self._org is None:
            if CURRENT_TASK and isinstance(CURRENT_TASK, Robot):
                # If CumulusCI is running a task, use that task's org
                return CURRENT_TASK.org_config
            else:
                self._org = self.keychain.get_org(self.org_name)
        return self._org

    @property
    def sf(self):
        if self._sf is None:
            self._sf = self._init_api()
        return self._sf

    @property
    def tooling(self):
        if self._tooling is None:
            self._tooling = self._init_api('tooling/')
        return self._tooling
        

    def set_login_url(self):
        """ Sets the LOGIN_URL variable in the suite scope which will
            automatically log into the target Salesforce org.
    
            Typically, this is run during Suite Setup
        """ 
        BuiltIn().set_suite_variable('${LOGIN_URL}', self.org.start_url)

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
        logger.console('\n')
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
        logger.console('\n')
        task_class, task_config = self._init_task(class_path, options, TaskConfig())
        return self._run_task(task_class, task_config)

    def _init_api(self, base_url=None):
        api_version = self.project_config.project__package__api_version

        rv = Salesforce(
            instance=self.org.instance_url.replace('https://', ''),
            session_id=self.org.access_token,
            version=api_version,
        )
        if base_url is not None:
            rv.base_url += base_url
        return rv

    def _init_task(self, class_path, options, task_config):
        task_class = import_class(class_path)
        task_config = self._parse_task_options(options, task_class, task_config)
        return task_class, task_config

    def _parse_task_options(self, options, task_class, task_config):
        if 'options' not in task_config.config:
            task_config.config['options'] = {}
        # Parse options and add to task config
        if options:
            for name, value in options.items():
                # Validate the option
                if name not in task_class.task_options:
                    raise TaskOptionsError(
                        'Option "{}" is not available for task {}'.format(
                            name,
                            task_name,
                        ),
                    )
    
                # Override the option in the task config
                task_config.config['options'][name] = value

        return task_config
    
    def _run_task(self, task_class, task_config):
        exception = None

        task = task_class(self.project_config,
                          task_config, org_config=self.org)

        task()
        return task.return_values


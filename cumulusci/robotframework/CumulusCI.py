import logging
from cumulusci.cli.config import CliConfig
from cumulusci.core.utils import import_class
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.config import TaskConfig
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
        self.sf = self._init_api()
        self.tooling = self._init_api('tooling/')
        # Turn off info logging of all http requests 
        logging.getLogger('requests.packages.urllib3.connectionpool').setLevel(logging.WARN)

    @property
    def config(self):
        if not hasattr(self, '_config'):
            self._config = self._init_config()
        return self._config

    @property
    def org(self):
        if not hasattr(self, '_org'):
            self._org = self.config.keychain.get_org(self.org_name)
        return self._org

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
            org = self.config.keychain.get_org(org)
        return org.start_url

    def run_task(self, task_name, **options):
        """ Runs a named CumulusCI task for the current project with optional
            support for overriding task options via kwargs.
            
            Examples:
            | =Keyword= | =task_name= | =task_options=             | =comment=                        |
            | Run Task  | deploy      |                            | Run deploy with standard options |
            | Run Task  | deploy      | path=path/to/some/metadata | Run deploy with custom path      |
        """
        task_config = getattr(self.config.project_config, 'tasks__{}'.format(task_name))
        if not task_config:
            raise TaskNotFoundError('Task not found: {}'.format(task_name))
        class_path = task_config.get('class_path')
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
        task_class, task_config = self._init_task(class_path, options, {})
        return self._run_task(task_class, task_config)

    def _init_api(self, base_url=None):
        api_version = self.config.project_config.project__package__api_version

        rv = Salesforce(
            instance=self.org.instance_url.replace('https://', ''),
            session_id=self.org.access_token,
            version=api_version,
        )
        if base_url is not None:
            rv.base_url += base_url
        return rv

    def _init_config(self):
        config = CliConfig()
        return config

    def _init_task(self, class_path, options, task_config):
        task_class = import_class(class_path)
        task_config = self._parse_task_options(options, task_class, task_config)
        return task_class, task_config

    def _parse_task_options(self, options, task_class, task_config):
        # Parse options and add to task config
        if options:
            if 'options' not in task_config:
                task_config['options'] = {}
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
                task_config['options'][name] = value

        return task_config
    
    def _run_task(self, task_class, task_config):
        task_config = TaskConfig(task_config)
        exception = None

        task = task_class(self.config.project_config,
                          task_config, org_config=self.org)

        task()
        return task.return_values


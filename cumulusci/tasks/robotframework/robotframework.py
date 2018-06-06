from cumulusci.core.exceptions import RobotTestFailure
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.salesforce import BaseSalesforceTask
from robot import run as robot_run
from robot.libdoc import libdoc
from robot.libraries.BuiltIn import BuiltIn
from robot.testdoc import testdoc

class Robot(BaseSalesforceTask):
    task_options = {
        'suites': {
            'description': 'Paths to test case files/directories to be executed similarly as when running the robot command on the command line.  Defaults to "tests" to run all tests in the tests directory',
            'required': True,
        },
        'tests': {
            'description': 'Run only tests matching name patterns.  Can be comma separated and use robot wildcards like *',
        }, 'include': {
            'description': 'Includes tests with a given tag',
        },
        'exclude': {
            'description': 'Excludes tests with a given tag',
        },
        'vars': {
            'description': 'Pass values to override variables in the format VAR1:foo,VAR2:bar',
        },
        'options': {
            'description': 'A dictionary of options to robot.run method.  See docs here for format.  NOTE: There is no cci CLI support for this option since it requires a dictionary.  Use this option in the cumulusci.yml when defining custom tasks where you can easily create a dictionary in yaml.',
        },
    }

    def _init_options(self, kwargs):
        super(Robot, self)._init_options(kwargs)

        if 'tests' in self.options:
            self.options['tests'] = process_list_arg(self.options['tests'])

        if 'include' in self.options:
            self.options['include'] = process_list_arg(self.options['include'])

        if 'exclude' in self.options:
            self.options['exclude'] = process_list_arg(self.options['exclude'])

        if 'vars' in self.options:
            self.options['vars'] = process_list_arg(self.options['vars'])
        else:
            self.options['vars'] = []
        self.options['vars'].append('org:{}'.format(self.org_config.name))

        # Initialize options as a dict
        if 'options' not in self.options:
            self.options['options'] = {}

    def _run_task(self):
        options = self.options['options'].copy()

        if 'tests' in self.options:
            options['test'] = self.options['tests']
        if 'include' in self.options:
            options['include'] = self.options['include']
        if 'exclude' in self.options:
            options['exclude'] = self.options['exclude']
        if 'vars' in self.options:
            options['variable'] = self.options['vars']

        # Inject CumulusCIRobotListener to build the CumulusCI library instance
        # from self.project_config instead of reinitializing CumulusCI's config
        #listener = CumulusCIRobotListener(self.project_config, self.org_config.name)
        #if 'listener' not in options:
        #    options['listener'] = []
        #options['listener'].append(listener)

        num_failed = robot_run(self.options['suites'], **options)
        if num_failed:
            raise RobotTestFailure("{} tests failed".format(num_failed))


class RobotLibDoc(BaseTask):
    task_options = {
        'path': {
            'description': "The path to the robot library to be documented.  Can be a python file or a .robot file.",
            'required': True,
        },
        'output': {
            'description': "The output file where the documentation will be written",
            'required': True,
        },
    }

    def _run_task(self):
        return libdoc(
            self.options['path'],
            self.options['output'],
        )

class RobotTestDoc(BaseTask):
    task_options = {
        'path': {
            'description': "The path containing .robot test files",
            'required': True,
        },
        'output': {
            'description': "The output html file where the documentation will be written",
            'required': True,
        },
    }

    def _run_task(self):
        return testdoc(
            self.options['path'],
            self.options['output'],
        )

from cumulusci.core.tasks import BaseTask
from cumulusci.tasks.salesforce import BaseSalesforceTask
from robot.conf import RobotSettings
from robot.running import TestSuiteBuilder
from robot.reporting import ResultWriter
from robot.libdoc import libdoc
from robot.libraries.BuiltIn import BuiltIn
from robot.output import pyloggingconf
from robot.testdoc import testdoc

class Robot(BaseSalesforceTask):
    task_options = {
        'suites': {
            'description': 'Paths to test case files/directories to be executed similarly as when running the robot command on the command line.  Defaults to "tests" to run all tests in the tests directory',
            'required': True,
        },
        'test': {
            'description': 'Run a specific test by name',
        },
        'include': {
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

        # Set default for suites
        if 'suites' not in self.options:
            self.options['suites'] = 'tests'

        # Initialize the include list and add the org name to it
        if 'include' in self.options:
            if not isinstance(self.options['include'], list):
                new_includes = []
                for include in self.options['include'].split(','):
                    new_includes.append(include.strip())
                self.options['include'] = new_includes

        # Initialize the exclude list and add the org name to it
        if 'exclude' in self.options:
            if not isinstance(self.options['exclude'], list):
                new_excludes = []
                for exclude in self.options['exclude'].split(','):
                    new_excludes.append(exclude.strip())
                self.options['exclude'] = new_excludes

        # Initialize the vars list and add the org name to it
        if 'vars' in self.options:
            if not isinstance(self.options['vars'], list):
                new_vars = []
                for var in self.options['vars'].split(','):
                    new_vars.append(var.strip())
                self.options['vars'] = new_vars
        else:
            self.options['vars'] = []
        self.options['vars'].append('ORG:{}'.format(self.org_config.name))

        # Initialize options as a dict
        if 'options' not in self.options:
            self.options['options'] = {}

    def _run_task(self):
        options = self.options['options'].copy()
        options['SuiteNames'] = self.options['suites']

        settings = RobotSettings(options)
        if 'test' in self.options:
            settings['TestNames'] = self.options['test']
        if 'include' in self.options:
            settings['Include'] = self.options['include']
        if 'exclude' in self.options:
            settings['Exclude'] = self.options['exclude']

        # Inject CumulusCIRobotListener to build the CumulusCI library instance
        # from self.project_config instead of reinitializing CumulusCI's config
        listener = CumulusCIRobotListener(self.project_config, self.org_config.name)
        settings['Listeners'] = [listener]

        # Build the top level test suite
        suite = TestSuiteBuilder().build(options['SuiteNames'])
        suite.configure(**settings.suite_config)

        # Run the test suite
        with pyloggingconf.robot_handler_enabled(settings.log_level):
            result = suite.run(settings)
            self.logger.info("Tests execution ended. Statistics:\n{}".format(result.suite.stat_message))
            if settings.log or settings.report or settings.xunit:
                writer = ResultWriter(settings.output if settings.log else result)
                writer.write_results(settings.get_rebot_settings())
        return result.return_code
        run(
            self.options['suites'], 
            variable=self.options['vars'],
            **self.options['options']
        )

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

class CumulusCIRobotListener(object):
    ROBOT_LISTENER_API_VERSION = 3

    def __init__(self, project_config, org_name):
        self.project_config = project_config
        self.org_name = org_name

    def start_suite(self, name, attributes):
        cumuluscilib = BuiltIn().import_library('cumulusci.robotframework.CumulusCI', self.org_name)
        cumuluscilib = BuiltIn().get_library_instance('cumulusci.robotframework.CumulusCI')
        if not hasattr(cumuluscilib, '_project_config'):
            cumuluscilib._project_config = self.project_config


from cumulusci.tasks.salesforce import BaseSalesforceTask
from robot.run import run

class Robot(BaseSalesforceTask):
    task_options = {
        'tests': {
            'description': 'Paths to test case files/directories to be executed similarly as when running the robot command on the command line.',
            'required': True,
        }
    }

    def _run_task(self):
        run(self.options['tests'], variables={'ORG', self.org_config.name})

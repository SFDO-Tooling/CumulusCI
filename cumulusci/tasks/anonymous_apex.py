from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import ApexCompilationException
from cumulusci.core.exceptions import ApexException
from cumulusci.core.exceptions import SalesforceException
from cumulusci.tasks.apex_logging import ApexLogger
import pprint


class AnonymousApexTask(BaseSalesforceApiTask):
    """ Executes a string of anonymous apex. """
    task_options = {
        'apex': {
            'description': 'The apex to run.',
            'required': True,
        }
    }

    def _run_task(self):
        self.logger.info('Executing Anonymous Apex')
        with ApexLogger(self) as apex_logs:
            result = self.tooling._call_salesforce(
                method='GET',
                url='{}executeAnonymous'.format(self.tooling.base_url),
                params={'anonymousBody': self.options['apex']},
            )
        pprint.pprint(apex_logs.logs)
        if result.status_code != 200:
            raise SalesforceException(
                result.status_code,
                result.content)
        # anon_results is an ExecuteAnonymous Result
        # https://developer.salesforce.com/docs/atlas.en-us.apexcode.meta/apexcode/sforce_api_calls_executeanonymous_result.htm

        anon_results = result.json()
        if not anon_results['compiled']:
            raise ApexCompilationException(
                anon_results['line'], anon_results['compileProblem'])

        if not anon_results['success']:
            raise ApexException(
                anon_results['exceptionMessage'], anon_results['exceptionStackTrace'])

        self.logger.info('Anonymous Apex Success')

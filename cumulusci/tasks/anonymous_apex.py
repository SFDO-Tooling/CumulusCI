from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import ApexCompilationException
from cumulusci.core.exceptions import ApexException
from cumulusci.core.exceptions import SalesforceException


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
        result = self.tooling._call_salesforce(
            method='GET',
            url='{}executeAnonymous'.format(self.tooling.base_url),
            params={'anonymousBody': self.options['apex']},
        )
        if result.status_code != 200:
            raise SalesforceGeneralError(url,
                                         path,
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
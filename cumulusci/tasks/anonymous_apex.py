from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.exceptions import ApexCompilationException
from cumulusci.core.exceptions import ApexException
from cumulusci.core.exceptions import SalesforceException
from cumulusci.tasks.apex_logging import ApexLogger


class AnonymousApexTask(BaseSalesforceApiTask):
    """ Executes a string of anonymous apex.

    `cci task run execute_anon -o apex 'System.debug(1);' -o system finest`

    does what you think it should
    """
    task_options = {
        'apex': {
            'description': 'The apex to run.',
            'required': True,
        },
        'profiling': {'description': 'The ApexProfiling log level'},
        'apexcode': {'description': 'The ApexCode log level'},
        'callout': {'description': 'The Callout log level'},
        'database': {'description': 'The database log level'},
        'system': {'description': 'The System log level'},
        'validation': {'description': 'The Validation log level'},
        'visualforce': {'description': 'The Visualforce log level'},
        'workflow': {'description': 'The Workflow log level'},
    }

    def _run_task(self):
        self.logger.info('Executing Anonymous Apex')
        self.apex_logs = ApexLogger(self,
                        profiling=self.options.get('profiling', None),
                        apex=self.options.get('apexcode', None),
                        callout=self.options.get('callout', None),
                        database=self.options.get('database', None),
                        system=self.options.get('system', None),
                        validation=self.options.get('validation', None),
                        visualforce=self.options.get('visualforce', None),
                        workflow=self.options.get('workflow', None),)
        # TODO: allow for manual apex log control instead                 
        with self.apex_logs:
        result = self.tooling._call_salesforce(
                method='GET',
                url='{}executeAnonymous'.format(self.tooling.base_url),
                params={'anonymousBody': self.options['apex']},
            )

        if result.status_code != 200:
            #TODO: is this the right exception
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

        for log_id in self.apex_logs.logs:
            self.logger.info(self.apex_logs.logs[log_id])

        return self.apex_logs.logs
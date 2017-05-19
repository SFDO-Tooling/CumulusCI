import pprint

from cumulusci.tasks.salesforce import BaseSalesforceToolingApiTask

class AnonymousApexTask(BaseSalesforceToolingApiTask):
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
        self.logger.info(pprint.pprint(result.json()))

import time

from cumulusci.core.tasks import BaseTask

class Sleep(BaseTask):
    name = 'Sleep'
    task_options = {
        'seconds': {
            'description': 'The number of seconds to sleep',
            'required': True,
        },
    } 
    
    def _run_task(self):
        self.logger.info("Sleeping for {} seconds".format(self.options['seconds']))
        time.sleep(self.options['seconds'])
        self.logger.info("Done")


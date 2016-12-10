import sarge

from cumulusci.core.exceptions import SalesforceDXException
from cumulusci.core.tasks import BaseTask

class BaseSalesforceDXTask(BaseTask):
    task_options = {
        'command': {
            'description': 'The Saleforce DX command to call.  For example: force:src:push',
            'required': True,
        },
        'options': {
            'description': 'The command line options to pass to the command',
        },
    }

    def _call_salesforce_dx(self, command, options=None):
        full_command = 'heroku ' + command
        if options:
            full_command += ' {}'.format(options)

        full_command += ' -u {}'.format(self.org_config.username)
        
        self.logger.info('Running: {}'.format(full_command))
        p = sarge.Command(full_command, stdout=sarge.Capture(buffer_size=-1))
        p.run()

        output = []
        for line in p.stdout:
            self.logger.info(line)

        if p.returncode:
            message = '{}: {}'.format(p.returncode, p.stdout)
            self.logger.error(message)
            raise SalesforceDXException(message)

    def _run_task(self):
        self._call_salesforce_dx(self.options['command'], self.options.get('options'))

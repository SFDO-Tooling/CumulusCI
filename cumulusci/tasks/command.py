import subprocess

from cumulusci.core.exceptions import CommandException
from cumulusci.core.tasks import BaseTask


class Command(BaseTask):

    task_options = {
        'command': {
            'description': 'The command to execute',
            'required': True,
        },
    }

    def _run_task(self):
        p = subprocess.Popen(
            self.options['command'],
            stdout=subprocess.PIPE,
            bufsize=1,
        )
        for line in iter(p.stdout.readline, ''):
            self.logger.info(line.strip())
        p.stdout.close()
        p.wait()
        if p.returncode:
            message = 'Return code: {}\nstderr: {}'.format(
                p.returncode,
                p.stderr,
            )
            self.logger.error(message)
            raise CommandException(message)

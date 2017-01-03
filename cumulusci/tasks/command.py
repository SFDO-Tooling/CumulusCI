import json
import os
import subprocess

from cumulusci.core.exceptions import CommandException
from cumulusci.core.tasks import BaseTask


class Command(BaseTask):

    task_options = {
        'command': {
            'description': 'The command to execute',
            'required': True,
        },
        'env': {
            'description': 'Environment variables to set for command. Must be flat dict, either as python dict from YAML or as JSON string.',
        }
    }

    def _run_task(self):
        env = os.environ.copy()
        new_env = self.options.get('env')
        if new_env:
            try:
                new_env = json.loads(new_env)
            except TypeError:
                # assume env is already dict
                pass
            for key in new_env.keys():
                env[key] = new_env[key]
        p = subprocess.Popen(
            self.options['command'],
            stdout=subprocess.PIPE,
            bufsize=1,
            env=env,
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

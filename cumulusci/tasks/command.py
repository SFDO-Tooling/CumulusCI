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
        'dir': {
            'description': 'If provided, the directory where the command should be run from.',
        },
        'env': {
            'description': 'Environment variables to set for command. Must be flat dict, either as python dict from YAML or as JSON string.',
        },
        'pass_env': {
            'description': 'If False, the current environment variables will not be passed to the child process.  Defaults to True',
            'required': True,
        },
    }

    def _init_options(self, kwargs):
        super(Command, self)._init_options(kwargs)
        if 'pass_env' not in self.options:
            self.options['pass_env'] = True
        if self.options['pass_env'] == 'False':
            self.options['pass_env'] = False
        if 'dir' not in self.options or not self.options['dir']:
            self.options['dir'] = '.'
        if 'env' not in self.options:
            self.options['env'] = {}
        else:
            try:
                self.options['env'] = json.loads(self.options['env'])
            except TypeError:
                # assume env is already dict
                pass

    def _run_task(self):
        env = self._get_env()
        self._run_command(env)
        
    def _get_env(self):
        if self.options['pass_env']:
            env = os.environ.copy()
        else:
            env = {}

        env.update(self.options['env'])
        return env

    def _process_output(self, line):
        self.logger.info(line.rstrip())
       
    def _handle_returncode(self, returncode): 
        if returncode:
            message = 'Return code: {}\nstderr: {}'.format(
                p.returncode,
                p.stderr,
            )
            self.logger.error(message)
            raise CommandException(message)

    def _run_command(self, env):
        p = subprocess.Popen(
            self.options['command'],
            stdout=subprocess.PIPE,
            bufsize=1,
            shell=True,
            executable='/bin/bash',
            env=env,
            cwd=self.options.get('dir'),
        )
        for line in iter(p.stdout.readline, ''):
            self._process_output(line)
        p.stdout.close()
        p.wait()
        if p.returncode:
            message = 'Return code: {}\nstderr: {}'.format(
                p.returncode,
                p.stderr,
            )
            self.logger.error(message)
            raise CommandException(message)

class SalesforceCommand(Command):
    """ A command that automatically gets a refreshed SF_ACCESS_TOKEN and SF_INSTANCE_URL passed as env vars """
    salesforce_task = True

    def _update_credentials(self):
        self.org_config.refresh_oauth_token(self.project_config.keychain.get_connected_app())

    def _get_env(self):
        env = super(SalesforceCommand, self)._get_env()
        env['SF_ACCESS_TOKEN'] = self.org_config.access_token
        env['SF_INSTANCE_URL'] = self.org_config.instance_url
        return env

task_options = Command.task_options.copy()
task_options['use_saucelabs'] = {
    'description': 'If True, use SauceLabs to run the tests.  The SauceLabs credentials will be fetched from the saucelabs service in the keychain and passed as environment variables to the command.  Defaults to False to run tests in the local browser.',
    'required': True,
}
class SalesforceBrowserTest(SalesforceCommand):
    """ A wrapper around browser test commands targetting a Salesforce org with support for running in local browser or on SauceLabs """

    task_options = task_options

    def _init_options(self, kwargs):
        super(SalesforceBrowserTest, self)._init_options(kwargs)
        if 'use_saucelabs' not in self.options or self.options['use_saucelabs'] == 'False':
            self.options['use_saucelabs'] = False
    
    def _get_env(self):
        env = super(SalesforceBrowserTest, self)._get_env()
        if self.options['use_saucelabs']:
            saucelabs = self.project_config.keychain.get_service('saucelabs')
            env['SAUCE_NAME'] = saucelabs.username
            env['SAUCE_KEY'] = saucelabs.api_key
            env['RUN_ON_SAUCE'] = 'True'
        else:
            env['RUN_LOCAL'] = 'True'
        return env

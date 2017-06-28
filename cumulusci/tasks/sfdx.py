""" Wrapper tasks for the SFDX CLI


TODO: Instead of everyone overriding random attrs, especially as future
users subclass these tasks, we should expose an api for the string format
function. i.e. make it easy for subclasses to add to the string inherited
from the base.

Actually do this in Command. have it expose command segments.

Then here in SFDX we will add an additional metalayer for
how the CLI formats args opts commands etc.
"""
import json

from cumulusci.core.config import ScratchOrgConfig
from cumulusci.tasks.command import Command

SFDX_CLI = 'sfdx'


class SFDXBaseTask(Command):
    """ Call the sfdx cli with params and no org """

    task_options = {
        'command': {
            'description': 'The full command to run with the sfdx cli.',
            'required': True,
        },
        'extra': {
            'description': 'Append additional options to the command',
        },
    }

    def _init_options(self, kwargs):
        super(SFDXBaseTask, self)._init_options(kwargs)
        self.options['command'] = self._get_command()

    def _get_command(self):
        command = '{SFDX_CLI} {command}'.format(
            command=self.options['command'],
            SFDX_CLI=SFDX_CLI
        )
        return command


class SFDXOrgTask(SFDXBaseTask):
    """ Call the sfdx cli with a workspace username """

    salesforce_task = True

    def _init_options(self, kwargs):
        super(SFDXOrgTask, self)._init_options(kwargs)

        # Add username to command if needed  
        self.options['command'] = self._add_username(self.options['command'])  

        # Add extra command args from
        if self.options.get('extra'):
            self.options['command'] += ' {}'.format(self.options['extra'])

        self.logger.info('Running command:  {}'.format(self.options['command']))

    def _add_username(self, command):
        # For scratch orgs, just pass the username in the command line
        if isinstance(self.org_config, ScratchOrgConfig):
            command += ' -u {username}'.format(
                username=self.org_config.username,
            )
        return command

    def _get_env(self):
        env = super(SFDXOrgTask, self)._get_env()
        if not isinstance(self.org_config, ScratchOrgConfig):
            # For non-scratch keychain orgs, pass the access token via env var
            env['SFDX_INSTANCE_URL'] = self.org_config.instance_url
            env['SFDX_USERNAME'] = self.org_config.access_token
        return env

class SFDXJsonTask(SFDXOrgTask):
    command = 'force:mdapi:deploy --json'

    def _process_output(self, line):
        try:
            data = json.loads(line)
        except:
            self.logger.error('Failed to parse json from line: {}'.format(line))
        
        self._process_data(data)

    def _init_options(self, kwargs):
        kwargs['command'] = self._get_command()
        super(SFDXJsonTask, self)._init_options(kwargs)

    def _get_command(self):
        command = '{SFDX_CLI} {command}'.format(
            command=self.command,
            SFDX_CLI=SFDX_CLI,
        )
        command = self._add_username(command)
        return command

    def _process_data(self, data):
        self.logger.info('JSON = {}'.format(data))

class SFDXJsonPollingTask(SFDXJsonTask):

    def _init_task(self):
        super(SFDXJsonPollingTask, self)._init_task()
        self.job_id = None

    def _process_output(self, line):
        started = False
        if hasattr(self, 'job_id'):
            started = True

        super(SFDXJsonPollingTask, self)._process_output(line)

        if not started:
            self._process_data(data)
        else:
            self._process_poll_data(data)

    def _process_data(self, data):
        if self.job_id:
            return self._process_poll_data(data) 

        self.job_id = data['id']
        self._poll()

    def _process_poll_data(self, data):
        self.logger.info(data)
        if self._check_poll_done(data):
            self.poll_complete = True

    def _poll_action(self):
        command = self._get_poll_command()
        env = self._get_env()
        self._run_command(
            env,
            command = command,
        )
        

    def _check_poll_done(self, data):
        return data.get('done', True)

    def _process_poll_output(self, line):
        pass

    def _get_poll_command(self):
        raise NotImplementedError(
            'Subclassess should provide an implementation'
        )
    

class SFDXDeploy(SFDXJsonPollingTask):
    """ Use sfdx force:mdapi:deploy to deploy a local directory of metadata """

    task_options = {
        'path': {
            'description': 'The path of the metadata to be deployed.',
            'required': True,
        },
    }

    def _get_command(self):
        command = super(SFDXDeploy, self)._get_command()
        if hasattr(self, 'options'):
            command += ' -d {}'.format(self.options.get('path', 'NO_PATH_PROVIDED'))
        return command

    def _get_poll_command(self):
        if not self.job_id:
            return None
        command = super(SFDXDeploy, self)._get_command()
        command += ' -i {}'.format(self.job_id)
        return command

    def _init_options(self, kwargs):
        super(SFDXDeploy, self)._init_options(kwargs)
        # Rewrite the command with the path merged in
        self.options['command'] = self._get_command()

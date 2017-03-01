""" Wrapper tasks for the SFDX CLI """

from cumulusci.tasks.command import Command
from cumulusci.tasks.command import SalesforceCommand

SFDX_CLI = 'sfdx'

class SFDXBaseTask(Command):
    """ Call the sfdx cli with params and no org """

    task_options = {
        'command': {
            'description': 'The full command to run with the sfdx cli.',
            'required': True
        }
    }

    def _init_options(self, kwargs):
        super(SFDXBaseTask, self)._init_options(kwargs)
        self.options['command'] = '{SFDX_CLI} {command}'.format(
            command=self.options['command'],
            SFDX_CLI=SFDX_CLI
        )


class SFDXOrgTask(SFDXBaseTask):
    """ Call the sfdx cli with a workspace username """

    def _init_options(self, kwargs):
        super(SFDXOrgTask, self)._init_options(kwargs)
        self.options['command'] = '{SFDX_CLI} {command} -u {username}'.format(
            command=self.options['command'],
            SFDX_CLI=SFDX_CLI,
            username=self.org_config.username
        )


class SFDXKeychainOrgTask(SFDXBaseTask, SalesforceCommand):
    """ Call the sfdx cli with the access token from a keychain org """

    def _get_env(self):
        env = super(SFDXKeychainOrgTask, self)._get_env()
        env['SFDX_INSTANCE_URL'] = None
        env['SFDX_USERNAME'] = self.org_config.access_token
        return env

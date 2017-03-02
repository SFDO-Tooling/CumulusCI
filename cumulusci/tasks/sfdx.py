""" Wrapper tasks for the SFDX CLI


TODO: Instead of everyone overriding random attrs, especially as future
users subclass these tasks, we should expose an api for the string format
function. i.e. make it easy for subclasses to add to the string inherited
from the base.

Actually do this in Command. have it expose command segments.

Then here in SFDX we will add an additional metalayer for
how the CLI formats args opts commands etc.
"""

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

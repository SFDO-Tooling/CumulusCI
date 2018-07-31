from __future__ import unicode_literals
import datetime
import json
import os
import re

import sarge
from simple_salesforce import Salesforce

from cumulusci.core.config import FAILED_TO_CREATE_SCRATCH_ORG
from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import ScratchOrgException


class ScratchOrgConfig(OrgConfig):
    """ Salesforce DX Scratch org configuration """

    @property
    def scratch_info(self):
        if hasattr(self, '_scratch_info'):
            return self._scratch_info

        # Create the org if it hasn't already been created
        if not self.created:
            self.create_org()

        self.logger.info('Getting scratch org info from Salesforce DX')

        # Call force:org:display and parse output to get instance_url and
        # access_token
        command = sarge.shell_format('sfdx force:org:display -u {0} --json', self.username)
        p = sarge.Command(
            command,
            stderr=sarge.Capture(buffer_size=-1),
            stdout=sarge.Capture(buffer_size=-1),
            shell=True
        )
        p.run()

        org_info = None
        stderr_list = [line.strip() for line in p.stderr]
        stdout_list = [line.strip() for line in p.stdout]

        if p.returncode:
            self.logger.error('Return code: {}'.format(p.returncode))
            for line in stderr_list:
                self.logger.error(line)
            for line in stdout_list:
                self.logger.error(line)
            message = '\nstderr:\n{}'.format('\n'.join(stderr_list))
            message += '\nstdout:\n{}'.format('\n'.join(stdout_list))
            raise ScratchOrgException(message)

        else:
            json_txt = ''.join(stdout_list)

            try:
                org_info = json.loads(''.join(stdout_list))
            except Exception as e:
                raise ScratchOrgException(
                    'Failed to parse json from output. This can happen if '
                    'your scratch org gets deleted.\n  '
                    'Exception: {}\n  Output: {}'.format(
                        e.__class__.__name__,
                        ''.join(stdout_list),
                    )
                )
            org_id = org_info['result']['accessToken'].split('!')[0]

        if 'password' in org_info['result'] and org_info['result']['password']:
            password = org_info['result']['password']
        else:
            password = self.config.get('password')

        self._scratch_info = {
            'instance_url': org_info['result']['instanceUrl'],
            'access_token': org_info['result']['accessToken'],
            'org_id': org_id,
            'username': org_info['result']['username'],
            'password': password,
        }

        self.config.update(self._scratch_info)

        self._scratch_info_date = datetime.datetime.utcnow()

        return self._scratch_info

    @property
    def access_token(self):
        return self.scratch_info['access_token']

    @property
    def instance_url(self):
        return self.scratch_info['instance_url']

    @property
    def org_id(self):
        org_id = self.config.get('org_id')
        if not org_id:
            org_id = self.scratch_info['org_id']
        return org_id

    @property
    def user_id(self):
        if not self.config.get('user_id'):
            sf = Salesforce(
                instance=self.instance_url.replace('https://', ''),
                session_id=self.access_token,
                version='38.0',
            )
            result = sf.query_all(
                "SELECT Id FROM User WHERE UserName='{}'".format(
                    self.username
                )
            )
            self.config['user_id'] = result['records'][0]['Id']
        return self.config['user_id']

    @property
    def username(self):
        username = self.config.get('username')
        if not username:
            username = self.scratch_info['username']
        return username

    @property
    def password(self):
        password = self.config.get('password')
        if not password:
            password = self.scratch_info['password']
        return password

    @property
    def days(self):
        return self.config.setdefault('days', 1)

    @property
    def expired(self):
        return self.expires and self.expires < datetime.datetime.now()

    @property
    def expires(self):
        if self.date_created:
            return self.date_created + datetime.timedelta(days=int(self.days))

    @property
    def days_alive(self):
        if self.expires:
            delta = datetime.datetime.now() - self.date_created 
            return delta.days + 1

    def create_org(self):
        """ Uses sfdx force:org:create to create the org """
        if not self.config_file:
            # FIXME: raise exception
            return
        if not self.scratch_org_type:
            self.config['scratch_org_type'] = 'workspace'

        options = {
            'config_file': self.config_file,
            'devhub': ' --targetdevhubusername {}'.format(self.devhub) if self.devhub else '',
            'namespaced': ' -n' if not self.namespaced else '',
            'days': ' --durationdays {}'.format(self.days) if self.days else '',
            'alias': sarge.shell_format(' -a "{0!s}"', self.sfdx_alias) if self.sfdx_alias else '',
            'extraargs': os.environ.get('SFDX_ORG_CREATE_ARGS', ''),
        }

        # This feels a little dirty, but the use cases for extra args would mostly
        # work best with env vars
        command = 'sfdx force:org:create -f {config_file}{devhub}{namespaced}{days}{alias} {extraargs}'.format(**options)
        self.logger.info(
            'Creating scratch org with command {}'.format(command))
        p = sarge.Command(command, stdout=sarge.Capture(buffer_size=-1), shell=True)
        p.run()

        org_info = None
        re_obj = re.compile(
            'Successfully created scratch org: (.+), username: (.+)')
        stdout = []
        for line in p.stdout:
            match = re_obj.search(line)
            if match:
                self.config['org_id'] = match.group(1)
                self.config['username'] = match.group(2)
            stdout.append(line)
            self.logger.info(line)

        self.config['date_created'] = datetime.datetime.now()

        if p.returncode:
            message = '{}: \n{}'.format(
                FAILED_TO_CREATE_SCRATCH_ORG,
                ''.join(stdout),
            )
            raise ScratchOrgException(message)

        if self.config.get('set_password'):
            self.generate_password()

        # Flag that this org has been created
        self.config['created'] = True

    def generate_password(self):
        """Generates an org password with the sfdx utility. """

        if self.password_failed:
            self.logger.warn(
                'Skipping resetting password since last attempt failed')
            return

        # Set a random password so it's available via cci org info
        command = sarge.shell_format('sfdx force:user:password:generate -u {0}', self.username)
        self.logger.info(
            'Generating scratch org user password with command {}'.format(command))
        p = sarge.Command(command, stdout=sarge.Capture(
            buffer_size=-1), stderr=sarge.Capture(buffer_size=-1), shell=True)
        p.run()

        stdout = []
        for line in p.stdout:
            stdout.append(line)
        stderr = []
        for line in p.stderr:
            stderr.append(line)

        if p.returncode:
            self.config['password_failed'] = True
            # Don't throw an exception because of failure creating the
            # password, just notify in a log message
            self.logger.warn(
                'Failed to set password: \n{}\n{}'.format(
                    '\n'.join(stdout), '\n'.join(stderr))
            )

    def delete_org(self):
        """ Uses sfdx force:org:delete to create the org """
        if not self.created:
            self.logger.info(
                'Skipping org deletion: the scratch org has not been created')
            return

        command = sarge.shell_format('sfdx force:org:delete -p -u {0}', self.username)
        self.logger.info(
            'Deleting scratch org with command {}'.format(command))
        p = sarge.Command(command, stdout=sarge.Capture(buffer_size=-1), shell=True)
        p.run()

        org_info = None
        stdout = []
        for line in p.stdout:
            stdout.append(line)
            if line.startswith('An error occurred deleting this org'):
                self.logger.error(line)
            else:
                self.logger.info(line)

        if p.returncode:
            message = 'Failed to delete scratch org: \n{}'.format(
                ''.join(stdout))
            raise ScratchOrgException(message)

        # Flag that this org has been created
        self.config['created'] = False
        self.config['username'] = None

    def force_refresh_oauth_token(self):
        # Call force:org:display and parse output to get instance_url and
        # access_token
        command = sarge.shell_format('sfdx force:org:open -r -u {0}', self.username)
        self.logger.info(
            'Refreshing OAuth token with command: {}'.format(command))
        p = sarge.Command(command, stdout=sarge.Capture(buffer_size=-1), shell=True)
        p.run()

        stdout_list = []
        for line in p.stdout:
            stdout_list.append(line.strip())

        if p.returncode:
            self.logger.error('Return code: {}'.format(p.returncode))
            for line in stdout_list:
                self.logger.error(line)
            message = 'Message: {}'.format('\n'.join(stdout_list))
            raise ScratchOrgException(message)

    def refresh_oauth_token(self, keychain=None):
        """ Use sfdx force:org:describe to refresh token instead of built in OAuth handling """
        if hasattr(self, '_scratch_info'):
            # Cache the scratch_info for 1 hour to avoid unnecessary calls out
            # to sfdx CLI
            delta = datetime.datetime.utcnow() - self._scratch_info_date
            if delta.total_seconds() > 3600:
                del self._scratch_info

                # Force a token refresh
                self.force_refresh_oauth_token()

        # Get org info via sfdx force:org:display
        self.scratch_info

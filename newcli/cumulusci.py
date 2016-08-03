import os

import click

from core.config import YamlGlobalConfig
from core.config import YamlProjectConfig
from core.config import EncryptedProjectKeychain
from core.config import ConnectedAppOAuthConfig
from core.config import OrgConfig
from core.exceptions import KeychainKeyNotFound

from oauth.salesforce import CaptureSalesforceOAuth

class CliConfig(object):
    def __init__(self):
        self.global_config = None
        self.project_config = None
        self.keychain = None

        self._load_global_config()
        self._load_project_config()
        self._load_keychain()

    def _load_global_config(self):
        self.global_config = YamlGlobalConfig()

    def _load_project_config(self):
        self.project_config = self.global_config.get_project_config()

    def _load_keychain(self):
        self.keychain_key = os.environ.get('CUMULUSCI_KEY')
        if self.project_config and self.keychain_key:
            self.keychain = EncryptedProjectKeychain(self.project_config, self.keychain_key)
            self.project_config.set_keychain(self.keychain)

pass_config = click.make_pass_decorator(CliConfig, ensure=True)

# Root command
@click.group('cli')
@pass_config
def cli(config):
    pass

# Top Level Groups    
@click.group('project', help="Commands for interacting with project repository configurations")
@pass_config
def project(config):
    pass

@click.group('org', help="Commands for connecting and interacting with Salesforce orgs")
@pass_config
def org(config):
    pass

@click.group('task', help="Commands for finding and running tasks for a project")
@pass_config
def task(config):
    pass

@click.group('flow', help="Commands for finding and running flows for a project")
@pass_config
def flow(config):
    pass

cli.add_command(project)
cli.add_command(org)
cli.add_command(task)
cli.add_command(flow)
       
# Commands for group: project

@click.command(name='init', help="Initialize a new project for use with the cumulusci toolbelt")
@pass_config
def project_init(config):
    pass

@click.command(name='info', help="Display information about the current project's configuration")
@pass_config
def project_info(config):
    pass

@click.command(name='list', help="List projects and their locations")
@pass_config
def project_list(config):
    pass

@click.command(name='cd', help="Change to the project's directory")
@pass_config
def project_cd(config):
    pass

project.add_command(project_init)
project.add_command(project_info)
project.add_command(project_list)
project.add_command(project_cd)

def check_keychain(config):
    if not config.keychain_key:
        raise KeychainKeyNotFound('You must set the environment variable CUMULUSCI_KEY with the encryption key to be used for storing org credentials')

# Commands for group: org
@click.command(name='browser', help="Opens a browser window and logs into the org using the stored OAuth credentials")
@click.argument('org_name')
@pass_config
def org_browser(config, org_name):
    pass

@click.command(name='connect', help="Connects a new org's credentials using OAuth Web Flow")
@click.argument('org_name')
@click.option('--sandbox', is_flag=True, help="If set, connects to a Salesforce sandbox org")
@pass_config
def org_connect(config, org_name, sandbox):
    check_keychain(config)

    oauth_capture = CaptureSalesforceOAuth(
        client_id = config.keychain.app.client_id,
        client_secret = config.keychain.app.client_secret,
        callback_url = config.keychain.app.callback_url,
        sandbox = sandbox,
        scope = 'web full refresh_token'
    ) 
    oauth_dict = oauth_capture()
    org_config = OrgConfig(oauth_dict)
    
    config.keychain.set_org(org_name, org_config)

@click.command(name='info', help="Display information for a connected org")
@click.argument('org_name')
@pass_config
def org_info(config, org_name):
    check_keychain(config)
    click.echo(getattr(config.keychain, 'orgs__{}'.format(org_name)).config)

@click.command(name='list', help="Lists the connected orgs for the current project")
@pass_config
def org_list(config):
    click.echo(config.list_orgs())

@click.command(name='connected_app', help="Displays the ConnectedApp info used for OAuth connections")
@pass_config
def org_connected_app(config):
    check_keychain(config)
    click.echo(config.keychain.app.config)


@click.command(name='config_connected_app', help="Configures the connected app used for connecting to Salesforce orgs")
@click.option('--client_id', help="The Client ID from the connected app", prompt=True)
@click.option('--client_secret', help="The Client Secret from the connected app", prompt=True, hide_input=True)
@click.option('--callback_url', help="The callback_url configured on the Connected App", default='http://localhost:8080/callback')
@pass_config
def org_config_connected_app(config, client_id, client_secret, callback_url):
    check_keychain(config)
    app_config = ConnectedAppOAuthConfig()
    app_config.config = {
        'client_id': client_id,
        'client_secret': client_secret,
        'callback_url': callback_url,
    }
    config.keychain.set_connected_app(app_config)

org.add_command(org_browser)
org.add_command(org_connect)
org.add_command(org_info)
org.add_command(org_list)
org.add_command(org_connected_app)
org.add_command(org_config_connected_app)

# Commands for group: task
@click.command(name='list', help="List available tasks for the current context")
@pass_config
def task_list(config):
    for task in config.project_config.list_tasks():
        click.echo('{name}: {description}'.format(**task))

@click.command(name='info', help="Displays information for a task")
@click.argument('task_name')
@pass_config
def task_info(config, task_name):
    task_info = getattr(config.project_config, 'tasks__{}'.format(task_name))
    click.echo(task_info)

@click.command(name='run', help="Runs a task")
@pass_config
def task_run(config):
    pass

task.add_command(task_list)
task.add_command(task_info)
task.add_command(task_run)

# Commands for group: flow
@click.command(name='list', help="List available flows for the current context")
@pass_config
def flow_list(config):
    pass

@click.command(name='info', help="Displays information for a flow")
@pass_config
def flow_info(config):
    pass

@click.command(name='run', help="Runs a flow")
@pass_config
def flow_run(config):
    pass

flow.add_command(flow_list)
flow.add_command(flow_info)
flow.add_command(flow_run)

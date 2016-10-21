import os
import webbrowser

import click

from cumulusci.core.config import YamlGlobalConfig
from cumulusci.core.config import YamlProjectConfig
from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import KeychainConnectedAppNotFound
from cumulusci.core.exceptions import KeychainKeyNotFound
from cumulusci.core.exceptions import ProjectConfigNotFound
from cumulusci.core.utils import import_class

from cumulusci.oauth.salesforce import CaptureSalesforceOAuth

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
        try:
            self.project_config = self.global_config.get_project_config()
        except ProjectConfigNotFound:
            pass

    def _load_keychain(self):
        self.keychain_key = os.environ.get('CUMULUSCI_KEY')
        if self.project_config and self.keychain_key:
            self.keychain_class = import_class(self.project_config.cumulusci__keychain)
            self.keychain = self.keychain_class(self.project_config, self.keychain_key)
            self.project_config.set_keychain(self.keychain)

pass_config = click.make_pass_decorator(CliConfig, ensure=True)

def check_connected_app(config):
    check_keychain(config)
    if not config.keychain.get_connected_app():
        raise click.UsageError("Please use the 'org config_connected_app' command to configure the OAuth Connected App to use for this project's keychain")
        

def check_keychain(config):
    check_project_config(config)
    if not config.keychain_key:
        raise click.UsageError('You must set the environment variable CUMULUSCI_KEY with the encryption key to be used for storing org credentials')

def check_project_config(config):
    if not config.project_config:
        raise click.UsageError('No project configuration found.  You can use the "project init" command to initilize the project for use with CumulusCI')

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
@click.option('--name', help="The project's package name", prompt=True)
@pass_config
def project_init(config, name):
    if not os.path.isdir('.git'):
        click.echo("You are not in the root of a Git repository")

    if os.path.isfile('cumulusci.yml'):
        click.echo("This project already has a cumulusci.yml file")

    f_yml = open('cumulusci.yml','w')

    yml_config = 'project:\n    name: {}\n'.format(name)
    f_yml.write(yml_config)

    click.echo("Your project is now initialized for use with CumulusCI")
    click.echo("You can use the project edit command to edit the project's config file")

@click.command(name='info', help="Display information about the current project's configuration")
@pass_config
def project_info(config):
    check_project_config(config)
    click.echo(config.project_config.project)

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

# Commands for group: org
@click.command(name='browser', help="Opens a browser window and logs into the org using the stored OAuth credentials")
@click.argument('org_name')
@pass_config
def org_browser(config, org_name):
    check_connected_app(config)

    org_config = config.project_config.get_org(org_name)
    org_config.refresh_oauth_token(config.keychain.get_connected_app())
    
    webbrowser.open(org_config.start_url)

@click.command(name='connect', help="Connects a new org's credentials using OAuth Web Flow")
@click.argument('org_name')
@click.option('--sandbox', is_flag=True, help="If set, connects to a Salesforce sandbox org")
@pass_config
def org_connect(config, org_name, sandbox):
    check_connected_app(config)

    connected_app = config.keychain.get_connected_app()
    
    oauth_capture = CaptureSalesforceOAuth(
        client_id = connected_app.client_id,
        client_secret = connected_app.client_secret,
        callback_url = connected_app.callback_url,
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
    check_connected_app(config)
    click.echo(config.keychain.get_org(org_name).config)

@click.command(name='list', help="Lists the connected orgs for the current project")
@pass_config
def org_list(config):
    check_connected_app(config)
    for org in config.project_config.list_orgs():
        click.echo('    {}'.format(org))

@click.command(name='connected_app', help="Displays the ConnectedApp info used for OAuth connections")
@pass_config
def org_connected_app(config):
    check_connected_app(config)
    click.echo(config.keychain.get_connected_app().config)


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
    check_project_config(config)
    for task in config.project_config.list_tasks():
        click.echo('{name}: {description}'.format(**task))

@click.command(name='info', help="Displays information for a task")
@click.argument('task_name')
@pass_config
def task_info(config, task_name):
    check_project_config(config)
    task_config = getattr(config.project_config, 'tasks__{}'.format(task_name))
    class_path = task_config.get('class_path')
    task_class = import_class(class_path)
    
    # General task info
    click.echo('Description: {}'.format(task_config.get('description')))
    click.echo('Class: {}'.format(task_config.get('class_path')))

    # Default options
    default_options = task_config.get('options', {})
    if default_options:
        click.echo('')
        click.echo('Default Option Values')
        for key, value in default_options.items():
            click.echo('    {}: {}'.format(key, value))

    # Task options
    task_options = getattr(task_class, 'task_options', {})
    if task_options:
        click.echo('')
        click.echo('Options:')
        for key, option in task_options.items():
            if option.get('required'):
                click.echo('  * {}: {}'.format(key, option.get('description')))
        for key, option in getattr(task_class, 'task_options', {}).items():
            if not option.get('required'):
                click.echo('    {}: {}'.format(key, option.get('description')))

@click.command(name='run', help="Runs a task")
@click.argument('task_name')
@click.argument('org_name')
@click.option('-o', nargs=2, multiple=True)
@pass_config
def task_run(config, task_name, org_name, o):
    # Check environment
    check_keychain(config)

    # Get necessary configs
    org_config = config.project_config.get_org(org_name)
    task_config = getattr(config.project_config, 'tasks__{}'.format(task_name))

    # Get the class to look up options
    class_path = task_config.get('class_path')
    task_class = import_class(class_path)

    # Parse command line options and add to task config
    if o:
        if 'options' not in task_config:
            task_config['options'] = {}
        for option in o:
            name = option[0]
            value = option[1]

            # Validate the option
            if name not in task_class.task_options:
                raise click.UsageError(
                    'Option "{}" is not available for task {}'.format(
                        name,
                        task_name,
                    )
                )

            # Override the option in the task config
            task_config['options'][name] = value
    
    # Create and run the task    
    task = task_class(config.project_config, task_config, org_config)
    click.echo(task())

# Add the task commands to the task group
task.add_command(task_list)
task.add_command(task_info)
task.add_command(task_run)

# Commands for group: flow
@click.command(name='list', help="List available flows for the current context")
@pass_config
def flow_list(config):
    check_project_config(config)
    click.echo(config.project_config.flows)

@click.command(name='info', help="Displays information for a flow")
@click.argument('flow_name')
@pass_config
def flow_info(config, flow_name):
    check_project_config(config)
    click.echo(getattr(config.project_config, 'flows__{}'.format(flow_name)))

@click.command(name='run', help="Runs a flow")
@click.argument('flow_name')
@click.argument('org_name')
@pass_config
def flow_run(config, flow_name, org_name):
    # Check environment
    check_keychain(config)

    # Get necessary configs
    org_config = config.project_config.get_org(org_name)
    flow_config = getattr(config.project_config, 'flows__{}'.format(flow_name))

    # Get the class to look up options
    class_path = flow_config.get('class_path', 'core.flows.BaseFlow')
    flow_class = import_class(class_path)

    # Create and run the flow 
    flow = flow_class(config.project_config, flow_config, org_config)
    click.echo(flow())

flow.add_command(flow_list)
flow.add_command(flow_info)
flow.add_command(flow_run)

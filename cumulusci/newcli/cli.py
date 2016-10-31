import json
import os
import sys
import webbrowser
import code

import click
from plaintable import Table

import cumulusci
from cumulusci.core.config import YamlGlobalConfig
from cumulusci.core.config import YamlProjectConfig
from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import ApexTestsDBConfig
from cumulusci.core.config import GithubConfig
from cumulusci.core.config import MrbelvedereConfig
from cumulusci.core.exceptions import ApexTestsDBNotConfigured
from cumulusci.core.exceptions import GithubNotConfigured
from cumulusci.core.exceptions import KeychainConnectedAppNotFound
from cumulusci.core.exceptions import KeychainKeyNotFound
from cumulusci.core.exceptions import MrbelvedereNotConfigured
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import ProjectConfigNotFound
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.exceptions import TaskRequiresSalesforceOrg
from cumulusci.core.utils import import_class

from cumulusci.oauth.salesforce import CaptureSalesforceOAuth

def pretty_dict(data):
    if not data:
        return ''
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))

class CliConfig(object):
    def __init__(self):
        self.global_config = None
        self.project_config = None
        self.keychain = None

        self._load_global_config()
        self._load_project_config()
        self._load_keychain()
        self._add_repo_to_path()

    def _add_repo_to_path(self):
        if self.project_config:
            sys.path.append(self.project_config.repo_root)

    def _load_global_config(self):
        try:
            self.global_config = YamlGlobalConfig()
        except NotInProject as e:
            raise click.UsageError(e.message)

    def _load_project_config(self):
        try:
            self.project_config = self.global_config.get_project_config()
        except ProjectConfigNotFound:
            pass
        except NotInProject as e:
            raise click.UsageError(e.message)

    def _load_keychain(self):
        self.keychain_key = os.environ.get('CUMULUSCI_KEY')
        if self.project_config and self.keychain_key:
            keychain_class = os.environ.get('CUMULUSCI_KEYCHAIN_CLASS')
            if not keychain_class:
                keychain_class = self.project_config.cumulusci__keychain
            self.keychain_class = import_class(keychain_class)
            self.keychain = self.keychain_class(self.project_config, self.keychain_key)
            self.project_config.set_keychain(self.keychain)

try:
    CLI_CONFIG = CliConfig()
except click.UsageError as e:
    click.echo(e.message)
    sys.exit(1)


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

@click.command(name='version', help='Print the current version of CumulusCI')
def version():
    click.echo(cumulusci.__version__)

@click.command(name='shell', help='Drop into a python shell')
@pass_config
def shell(config):
    code.interact(local=dict(globals(), **locals()))

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
cli.add_command(version)
cli.add_command(shell)

# Commands for group: project

@click.command(name='init',
    help="Initialize a new project for use with the cumulusci toolbelt",
)
@click.option('--name',
    help="The project's package name",
    prompt=True,
)
@click.option('--package-name',
    help="The project's package name",
    prompt=True,
)
@click.option('--package-namespace',
    help="The project's package namespace",
    prompt=True,
)
@click.option('--package-api-version',
    help="The Salesforce API verson for the package",
    prompt=True,
    default=CLI_CONFIG.global_config.project__package__api_version,
)
@click.option('--git-prefix-feature',
    help="The branch prefix for all feature branches",
    prompt=True,
    default=CLI_CONFIG.global_config.project__git__prefix_feature,
)
@click.option('--git-default-branch',
    help="The default branch in the repository",
    prompt=True,
    default=CLI_CONFIG.global_config.project__git__default_branch,
)
@click.option('--git-prefix-beta',
    help="The tag prefix for beta release tags",
    prompt=True,
    default=CLI_CONFIG.global_config.project__git__prefix_beta,
)
@click.option('--git-prefix-release',
    help="The tag prefix for production release tags",
    prompt=True,
    default=CLI_CONFIG.global_config.project__git__prefix_release,
)
@click.option('--test-namematch',
    help="The SOQL format like query for selecting Apex tests.  % is wildcard",
    prompt=True,
    default=CLI_CONFIG.global_config.project__test__namematch,
)
@pass_config
def project_init(config, name, package_name, package_namespace, package_api_version, git_prefix_feature, git_default_branch, git_prefix_beta, git_prefix_release, test_namematch):
    if not os.path.isdir('.git'):
        click.echo("You are not in the root of a Git repository")

    if os.path.isfile('cumulusci.yml'):
        click.echo("This project already has a cumulusci.yml file")

    f_yml = open('cumulusci.yml','w')

    yml_config = []
    # project:
    yml_config.append('project:')
    yml_config.append('    name: {}'.format(name))

    #     package:
    package_config = []
    if package_name and package_name != config.global_config.project__package__name:
        package_config.append('        name: {}'.format(package_name))
    if package_namespace and package_namespace != config.global_config.project__package__namespace:
        package_config.append('        namespace: {}'.format(package_namespace))
    if package_api_version and package_api_version != config.global_config.project__package__api_version:
        package_config.append('        api_version: {}'.format(package_api_version))
    if package_config:
        yml_config.append('    package:')
        yml_config.extend(package_config)

    #     git:
    git_config = []
    if git_prefix_feature and git_prefix_feature != config.global_config.project__git__prefix_feature:
        git_config.append('        feature: {}'.format(git_prefix_feature))
    if git_default_branch and git_default_branch != config.global_config.project__git__default_branch:
        git_config.append('        branch: {}'.format(git_default_branch))
    if git_prefix_beta and git_prefix_beta != config.global_config.project__git__prefix_beta:
        git_config.append('        beta: {}'.format(git_prefix_beta))
    if git_prefix_release and git_prefix_release != config.global_config.project__git__prefix_release:
        git_config.append('        release: {}'.format(git_prefix_release))
    if git_config:
        yml_config.append('    git:')
        yml_config.extend(git_config)


    #     test:
    test_config = []
    if test_namematch and test_namematch != config.global_config.project__test__namematch:
        test_config.append('        namematch: {}'.format(test_namematch))
    if test_config:
        yml_config.append('    test:')
        yml_config.extend(test_config)

    yml_config.append('')
    f_yml.write('\n'.join(yml_config))

    click.echo("Your project is now initialized for use with CumulusCI")
    click.echo("You can use the project edit command to edit the project's config file")

@click.command(name='info', help="Display information about the current project's configuration")
@pass_config
def project_info(config):
    check_project_config(config)
    click.echo(pretty_dict(config.project_config.project))

@click.command(name='connect_github', help="Configure this project for Github tasks")
@click.option('--username', help="The Github username to use for tasks", prompt=True)
@click.option('--password', help="The Github password to use for tasks.  It is recommended to use a Github Application Token instead of password to allow bypassing 2fa.", prompt=True, hide_input=True)
@click.option('--email', help="The email address to used by Github tasks when an operation requires an email address.", prompt=True)
@pass_config
def project_connect_github(config, username, password, email):
    check_keychain(config)
    config.keychain.set_github(GithubConfig({
        'username': username,
        'password': password,
        'email': email,
    }))
    click.echo('Github is now configured for this project')

@click.command(name='show_github', help="Prints the current Github configuration for this project")
@pass_config
def project_show_github(config):
    check_keychain(config)
    try:
        github = config.keychain.get_github()
        click.echo(pretty_dict(github.config))
    except GithubNotConfigured:
        click.echo('Github is not configured for this project.  Use project connect_github to configure.')


@click.command(name='connect_mrbelvedere', help="Configure this project for mrbelvedere tasks")
@click.option('--base_url', help="The base url for your mrbelvedere instance", prompt=True)
@click.option('--api_key', help="The package api_key for the package in your mrbelvedere instance.", prompt=True, hide_input=True)
@pass_config
def project_connect_mrbelvedere(config, base_url, api_key):
    check_keychain(config)
    config.keychain.set_mrbelvedere(MrbelvedereConfig({
        'base_url': base_url,
        'api_key': api_key,
    }))
    click.echo('Mrbelvedere is now configured for this project')

@click.command(name='show_mrbelvedere', help="Prints the current mrbelvedere configuration for this project")
@pass_config
def project_show_mrbelvedere(config):
    check_keychain(config)
    try:
        mrbelvedere = config.keychain.get_mrbelvedere()
        click.echo(pretty_dict(mrbelvedere.config))
    except MrbelvedereNotConfigured:
        click.echo('mrbelvedere is not configured for this project.  Use project connect_mrbelvedere to configure.')

@click.command(name='connect_apextestsdb', help="Configure this project for ApexTestsDB tasks")
@click.option('--base_url', help="The base url for your ApexTestsDB instance", prompt=True)
@click.option('--user-id', help="The user id to use when connecting to ApexTestsDB.", prompt=True)
@click.option('--token', help="The api token to use when connecting to ApexTestsDB.", prompt=True, hide_input=True)
@pass_config
def project_connect_apextestsdb(config, base_url, user_id, token):
    check_keychain(config)
    config.keychain.set_apextestsdb(ApexTestsDBConfig({
        'base_url': base_url,
        'user_id': user_id,
        'token': token,
    }))
    click.echo('ApexTestsDB is now configured for this project')

@click.command(name='show_apextestsdb', help="Prints the current ApexTestsDB configuration for this project")
@pass_config
def project_show_apextestsdb(config):
    check_keychain(config)
    try:
        apextestsdb = config.keychain.get_apextestsdb()
        click.echo(pretty_dict(apextestsdb.config))
    except ApexTestsDBNotConfigured:
        click.echo('ApexTestsDB is not configured for this project.  Use project connect_apextestsdb to configure.')


@click.command(name='list', help="List projects and their locations")
@pass_config
def project_list(config):
    pass

@click.command(name='cd', help="Change to the project's directory")
@pass_config
def project_cd(config):
    pass

project.add_command(project_connect_apextestsdb)
project.add_command(project_connect_github)
project.add_command(project_connect_mrbelvedere)
project.add_command(project_init)
project.add_command(project_info)
project.add_command(project_show_apextestsdb)
project.add_command(project_show_github)
project.add_command(project_show_mrbelvedere)
#project.add_command(project_list)
#project.add_command(project_cd)

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

@click.command(name='default', help="Sets an org as the default org for tasks and flows")
@click.argument('org_name')
@click.option('--unset', is_flag=True, help="Unset the org as the default org leaving no default org selected")
@pass_config
def org_default(config, org_name, unset):
    check_connected_app(config)

    if unset:
        org = config.keychain.unset_default_org()
        click.echo('{} is no longer the default org.  No default org set.'.format(org_name))
    else:
        org = config.keychain.set_default_org(org_name)
        click.echo('{} is now the default org'.format(org_name))


@click.command(name='info', help="Display information for a connected org")
@click.argument('org_name')
@pass_config
def org_info(config, org_name):
    check_connected_app(config)
    click.echo(pretty_dict(config.keychain.get_org(org_name).config))

@click.command(name='list', help="Lists the connected orgs for the current project")
@pass_config
def org_list(config):
    check_connected_app(config)
    data = []
    headers = ['org','is_default']
    for org in config.project_config.list_orgs():
        org_config = config.project_config.get_org(org)
        if org_config.default:
            data.append((org, '*'))
        else:
            data.append((org, ''))
    table = Table(data, headers)
    click.echo(table)

@click.command(name='connected_app', help="Displays the ConnectedApp info used for OAuth connections")
@pass_config
def org_connected_app(config):
    check_connected_app(config)
    click.echo(pretty_dict(config.keychain.get_connected_app().config))


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
org.add_command(org_default)
org.add_command(org_info)
org.add_command(org_list)
org.add_command(org_connected_app)
org.add_command(org_config_connected_app)

# Commands for group: task
@click.command(name='list', help="List available tasks for the current context")
@pass_config
def task_list(config):
    check_project_config(config)
    data = []
    headers = ['task', 'description']
    for task in config.project_config.list_tasks():
        data.append((task['name'], task['description']))
    table = Table(data, headers)
    click.echo(table)

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
        data = []
        headers = ['Option', 'Required', 'Description']
        for key, option in task_options.items():
            if option.get('required'):
                data.append((key, '*', option.get('description')))
            else:
                data.append((key, '', option.get('description')))
        table = Table(data, headers)
        click.echo(table)

@click.command(name='run', help="Runs a task")
@click.argument('task_name')
@click.option('--org', help="Specify the target org.  By default, runs against the current default org")
@click.option('-o', nargs=2, multiple=True)
@pass_config
def task_run(config, task_name, org, o):
    # Check environment
    check_keychain(config)

    # Get necessary configs
    if org:
        org_config = config.project_config.get_org(org)
    else:
        org_config = config.project_config.keychain.get_default_org()
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

    task_config = TaskConfig(task_config)

    # Create and run the task
    try:
        task = task_class(config.project_config, task_config, org_config = org_config)
    except TaskRequiresSalesforceOrg as e:
        raise click.UsageError('This task requires a salesforce org.  Use org default <name> to set a default org or pass the org name with the --org option')
    except TaskOptionsError as e:
        raise click.UsageError(e.message)

    try:
        task()
    except TaskOptionsError as e:
        raise click.UsageError(e.message)

# Add the task commands to the task group
task.add_command(task_list)
task.add_command(task_info)
task.add_command(task_run)

# Commands for group: flow
@click.command(name='list', help="List available flows for the current context")
@pass_config
def flow_list(config):
    check_project_config(config)
    data = []
    headers = ['flow', 'description']
    for flow in config.project_config.flows:
        description = getattr(config.project_config, 'flows__{}__description'.format(flow))
        data.append((flow, description))
    table = Table(data, headers)
    click.echo(table)

@click.command(name='info', help="Displays information for a flow")
@click.argument('flow_name')
@pass_config
def flow_info(config, flow_name):
    check_project_config(config)
    click.echo(pretty_dict(getattr(config.project_config, 'flows__{}'.format(flow_name))))

@click.command(name='run', help="Runs a flow")
@click.argument('flow_name')
@click.option('--org', help="Specify the target org.  By default, runs against the current default org")
@pass_config
def flow_run(config, flow_name, org):
    # Check environment
    check_keychain(config)

    # Get necessary configs
    if org:
        org_config = config.project_config.get_org(org)
    else:
        org_config = config.project_config.keychain.get_default_org()
    flow_config = getattr(config.project_config, 'flows__{}'.format(flow_name))

    # Get the class to look up options
    class_path = flow_config.get('class_path', 'cumulusci.core.flows.BaseFlow')
    flow_class = import_class(class_path)

    # Create the flow and handle initialization exceptions
    try:
        flow = flow_class(config.project_config, flow_config, org_config)
    except TaskRequiresSalesforceOrg as e:
        raise click.UsageError('This flow requires a salesforce org.  Use org default <name> to set a default org or pass the org name with the --org option')
    except TaskOptionsError as e:
        raise click.UsageError(e.message)

    # Run the flow and handle exceptions
    try:
        flow()
    except TaskOptionsError as e:
        raise click.UsageError(e.message)

flow.add_command(flow_list)
flow.add_command(flow_info)
flow.add_command(flow_run)

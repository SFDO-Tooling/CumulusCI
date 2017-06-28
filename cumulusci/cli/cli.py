import json
import os
import sys
import webbrowser
import code
import yaml

import click
from plaintable import Table
from rst2ansi import rst2ansi

import cumulusci
from cumulusci.core.config import ConnectedAppOAuthConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import YamlGlobalConfig
from cumulusci.core.config import YamlProjectConfig
from cumulusci.core.exceptions import ApexTestException
from cumulusci.core.exceptions import FlowNotFoundError
from cumulusci.core.exceptions import KeychainConnectedAppNotFound
from cumulusci.core.exceptions import KeychainKeyNotFound
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.salesforce_api.exceptions import MetadataComponentFailure
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import ProjectConfigNotFound
from cumulusci.core.exceptions import ScratchOrgException
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.exceptions import TaskRequiresSalesforceOrg
from cumulusci.core.utils import import_class
from cumulusci.utils import doc_task
from cumulusci.oauth.salesforce import CaptureSalesforceOAuth
from logger import init_logger


def pretty_dict(data):
    if not data:
        return ''
    return json.dumps(data, sort_keys=True, indent=4, separators=(',', ': '))

class CliConfig(object):
    def __init__(self):
        self.global_config = None
        self.project_config = None
        self.keychain = None

        init_logger()
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
        if self.project_config:
            keychain_class = os.environ.get(
                'CUMULUSCI_KEYCHAIN_CLASS',
                self.project_config.cumulusci__keychain,
            )
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
    if config.project_config.keychain and config.project_config.keychain.encrypted and not config.keychain_key:
        raise click.UsageError('You must set the environment variable CUMULUSCI_KEY with the encryption key to be used for storing org credentials')

def check_project_config(config):
    if not config.project_config:
        raise click.UsageError('No project configuration found.  You can use the "project init" command to initilize the project for use with CumulusCI')

def handle_sentry_event(config, no_prompt):
    event = config.project_config.sentry_event
    if not event:
        return

    sentry_config = config.project_config.keychain.get_service('sentry')
    event_url = '{}/{}/{}/?query={}'.format(
        config.project_config.sentry.remote.base_url,
        sentry_config.org_slug,
        sentry_config.project_slug,
        event,
    )
    click.echo('An error event was recorded in sentry.io and can be viewed at the url:\n{}'.format(event_url))

    if not no_prompt and click.confirm('Do you want to open a browser to view the error in sentry.io?'):
        webbrowser.open(event_url)

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
@click.pass_context
def shell(ctx,config):
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

@click.group('service',help="Commands for connecting services to the keychain")
@pass_config
def service(config):
    pass

cli.add_command(project)
cli.add_command(org)
cli.add_command(task)
cli.add_command(flow)
cli.add_command(version)
cli.add_command(shell)
cli.add_command(service)

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
@click.option('--test-name-match',
    help="The SOQL format like query for selecting Apex tests.  % is wildcard",
    prompt=True,
    default=CLI_CONFIG.global_config.project__test__name_match,
)
@pass_config
def project_init(config, name, package_name, package_namespace, package_api_version, git_prefix_feature, git_default_branch, git_prefix_beta, git_prefix_release, test_name_match):
    if not os.path.isdir('.git'):
        click.echo("You are not in the root of a Git repository")

    if os.path.isfile('cumulusci.yml'):
        click.echo("This project already has a cumulusci.yml file")

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
        git_config.append('        prefix_feature: {}'.format(git_prefix_feature))
    if git_default_branch and git_default_branch != config.global_config.project__git__default_branch:
        git_config.append('        default_branch: {}'.format(git_default_branch))
    if git_prefix_beta and git_prefix_beta != config.global_config.project__git__prefix_beta:
        git_config.append('        prefix_beta: {}'.format(git_prefix_beta))
    if git_prefix_release and git_prefix_release != config.global_config.project__git__prefix_release:
        git_config.append('        prefix_release: {}'.format(git_prefix_release))
    if git_config:
        yml_config.append('    git:')
        yml_config.extend(git_config)


    #     test:
    test_config = []
    if test_name_match and test_name_match != config.global_config.project__test__name_match:
        test_config.append('        name_match: {}'.format(test_name_match))
    if test_config:
        yml_config.append('    test:')
        yml_config.extend(test_config)

    yml_config.append('')
    
    with open('cumulusci.yml','w') as f_yml:
        f_yml.write('\n'.join(yml_config))

    click.echo("Your project is now initialized for use with CumulusCI")
    click.echo("You can use the project edit command to edit the project's config file")

@click.command(name='info', help="Display information about the current project's configuration")
@pass_config
def project_info(config):
    check_project_config(config)
    click.echo(pretty_dict(config.project_config.project))

@click.command(name="dependencies", help="Displays the current dependencies for the project.  If the dependencies section has references to other github repositories, the repositories are inspected and a static list of dependencies is created")
@pass_config
def project_dependencies(config):
    check_project_config(config)
    dependencies = config.project_config.get_static_dependencies()
    for line in config.project_config.pretty_dependencies(dependencies):
        click.echo(line)

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
project.add_command(project_dependencies)
#project.add_command(project_list)
#project.add_command(project_cd)

# Commands for group: service
@click.command(name='list', help='List services available for configuration and use')
@pass_config
def service_list(config):
    headers = ['service','description','is_configured']
    data = []
    for serv,schema in config.project_config.services.iteritems():
        is_configured = ''
        if serv in config.keychain.list_services():
            is_configured = '* '
        data.append((serv,schema['description'],is_configured))
    table = Table(data, headers)
    click.echo(table)


class ConnectServiceCommand(click.MultiCommand):
    def list_commands(self, ctx):
        """ list the services that can be configured """
        config = ctx.ensure_object(CliConfig)
        return sorted(config.project_config.services.keys())

    def _build_param(self, attribute, details):
        req = details['required']
        return click.Option(('--{0}'.format(attribute),), prompt=req, required=req)

    def get_command(self, ctx, name):
        config = ctx.ensure_object(CliConfig)

        attributes = getattr(
            config.project_config, 
            'services__{0}__attributes'.format(name)
        ).iteritems()
        params = [self._build_param(attr,cnfg) for attr, cnfg in attributes]
        params.append(click.Option(('--project',),is_flag=True))

        @click.pass_context
        def callback(ctx,project=False,*args, **kwargs):
            check_keychain(config)
            serv_conf = dict((k, v) for k, v in kwargs.iteritems() if v!=None) # remove None values
            config.keychain.set_service(name, ServiceConfig(serv_conf), project)
            if project:
                click.echo('{0} is now configured for this project'.format(name))
            else:
                click.echo('{0} is now configured for global use'.format(name))

        ret = click.Command(name, params=params, callback=callback)
        return ret

@click.command(cls=ConnectServiceCommand,name='connect',help='Connect a CumulusCI task service')
@click.pass_context
def service_connect(ctx, *args, **kvargs):
    pass


@click.command(name='show',help='Show the details of a connected service')
@click.argument('service_name')
@pass_config
def service_show(config,service_name):
    check_keychain(config)
    try:
        service_config = config.keychain.get_service(service_name)
        click.echo(pretty_dict(service_config.config))
    except ServiceNotConfigured:
        click.echo('{0} is not configured for this project.  Use service connect {0} to configure.'.format(service_name))

service.add_command(service_connect)
service.add_command(service_list)
service.add_command(service_show)

# Commands for group: org
@click.command(name='browser', help="Opens a browser window and logs into the org using the stored OAuth credentials")
@click.argument('org_name')
@pass_config
def org_browser(config, org_name):
    check_connected_app(config)

    org_config = config.project_config.get_org(org_name)
    org_config.refresh_oauth_token(config.keychain.get_connected_app())

    webbrowser.open(org_config.start_url)

    # Save the org config in case it was modified
    config.keychain.set_org(org_name, org_config)

@click.command(name='connect', help="Connects a new org's credentials using OAuth Web Flow")
@click.argument('org_name')
@click.option('--sandbox', is_flag=True, help="If set, connects to a Salesforce sandbox org")
@click.option('--login-url', help='If set, login to this hostname.', default= 'https://login.salesforce.com')
@click.option('--default', is_flag=True, help='If set, sets the connected org as the new default org')
@click.option('--global-org', help='Set True if org should be used by any project', is_flag=True)
@pass_config
def org_connect(config, org_name, sandbox, login_url, default, global_org):
    check_connected_app(config)

    connected_app = config.keychain.get_connected_app()
    if sandbox:
        login_url = 'https://test.salesforce.com'

    oauth_capture = CaptureSalesforceOAuth(
        client_id = connected_app.client_id,
        client_secret = connected_app.client_secret,
        callback_url = connected_app.callback_url,
        auth_site = login_url,
        scope = 'web full refresh_token'
    )
    oauth_dict = oauth_capture()
    org_config = OrgConfig(oauth_dict)
    org_config.load_userinfo()

    config.keychain.set_org(org_name, org_config, global_org)

    if default:
        org = config.keychain.set_default_org(org_name)
        click.echo('{} is now the default org'.format(org_name))

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
    
    org_config = config.keychain.get_org(org_name)
    
    try:
        org_config.refresh_oauth_token(config.keychain.get_connected_app())
    except ScratchOrgException as e:
        raise click.ClickException('ScratchOrgException: {}'.format(e.message))

    click.echo(pretty_dict(org_config.config))

    # Save the org config in case it was modified
    config.keychain.set_org(org_name, org_config)

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

@click.command(name='scratch', help="Connects a Salesforce DX Scratch Org to the keychain")
@click.argument('config_name')
@click.argument('org_name')
@click.option('--default', is_flag=True, help='If set, sets the connected org as the new default org')
@click.option('--delete', is_flag=True, help="If set, triggers a deletion of the current scratch org.  This can be used to reset the org as the org configuration remains to regenerate the org on the next task run.")
@click.option('--devhub', help="If provided, overrides the devhub used to create the scratch org")
@pass_config
def org_scratch(config, config_name, org_name, default, delete, devhub):
    check_connected_app(config)
  
    scratch_configs = getattr(config.project_config, 'orgs__scratch')
    if not scratch_configs:
        raise click.UsageError( 'No scratch org configs found in cumulusci.yml')
    scratch_config = scratch_configs.get(config_name)
    if not scratch_config:
        raise click.UsageError(
            'No scratch org config named {} found in the cumulusci.yml file'.format(config_name)
        )

    if devhub:
        scratch_config['devhub'] = devhub

    org_config = ScratchOrgConfig(scratch_config) 

    config.keychain.set_org(org_name, org_config)

    if default:
        org = config.keychain.set_default_org(org_name)
        click.echo('{} is now the default org'.format(org_name))

@click.command(name='scratch_delete', help="Deletes a Salesforce DX Scratch Org leaving the config in the keychain for regeneration")
@click.argument('org_name')
@pass_config
def org_scratch_delete(config, org_name):
    check_connected_app(config)
    org_config = config.keychain.get_org(org_name)
    if not org_config.scratch:
        raise click.UsageError('Org {} is not a scratch org'.format(org_name))

    try:
        org_config.delete_org()
    except ScratchOrgException as e:
        exception = click.UsageError(e.message)

    config.keychain.set_org(org_name, org_config)

@click.command(name='connected_app', help="Displays the ConnectedApp info used for OAuth connections")
@pass_config
def org_connected_app(config):
    check_connected_app(config)
    click.echo(pretty_dict(config.keychain.get_connected_app().config))


@click.command(name='config_connected_app', help="Configures the connected app used for connecting to Salesforce orgs")
@click.option('--client_id', help="The Client ID from the connected app", prompt=True)
@click.option('--client_secret', help="The Client Secret from the connected app", prompt=True, hide_input=True)
@click.option('--callback_url', help="The callback_url configured on the Connected App", default='http://localhost:8080/callback')
@click.option('--project', help='Set if storing encrypted keychain file in project directory', is_flag=True)
@pass_config
def org_config_connected_app(config, client_id, client_secret, callback_url, project):
    check_keychain(config)
    app_config = ConnectedAppOAuthConfig()
    app_config.config = {
        'client_id': client_id,
        'client_secret': client_secret,
        'callback_url': callback_url,
    }
    config.keychain.set_connected_app(app_config, project)

org.add_command(org_browser)
org.add_command(org_config_connected_app)
org.add_command(org_connect)
org.add_command(org_connected_app)
org.add_command(org_default)
org.add_command(org_info)
org.add_command(org_list)
org.add_command(org_scratch)
org.add_command(org_scratch_delete)

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

@click.command(name='doc', help="Exports RST format documentation for all tasks")
@pass_config
def task_doc(config):
    config_src = config.global_config
    
    for name, options in config_src.tasks.items():
        task_config = TaskConfig(options)
        doc = doc_task(name, task_config)
        click.echo(doc)
        click.echo('')

@click.command(name='info', help="Displays information for a task")
@click.argument('task_name')
@pass_config
def task_info(config, task_name):
    check_project_config(config)
    task_config = getattr(config.project_config, 'tasks__{}'.format(task_name))
    if not task_config:
        raise TaskNotFoundError('Task not found: {}'.format(task_name))

    task_config = TaskConfig(task_config)
    click.echo(rst2ansi(doc_task(task_name, task_config)))

@click.command(name='run', help="Runs a task")
@click.argument('task_name')
@click.option('--org', help="Specify the target org.  By default, runs against the current default org")
@click.option('-o', nargs=2, multiple=True, help="Pass task specific options for the task as '-o option value'.  You can specify more than one option by using -o more than once.")
@click.option('--debug', is_flag=True, help="Drops into pdb, the Python debugger, on an exception")
@click.option('--debug-before', is_flag=True, help="Drops into the Python debugger right before task start.")
@click.option('--debug-after', is_flag=True, help="Drops into the Python debugger at task completion.")
@click.option('--no-prompt', is_flag=True, help="Disables all prompts.  Set for non-interactive mode use such as calling from scripts or CI systems")
@pass_config
def task_run(config, task_name, org, o, debug, debug_before, debug_after, no_prompt):
    # Check environment
    check_keychain(config)

    # Get necessary configs
    if org:
        org_config = config.project_config.get_org(org)
    else:
        org, org_config = config.project_config.keychain.get_default_org()
    task_config = getattr(config.project_config, 'tasks__{}'.format(task_name))
    if not task_config:
        raise TaskNotFoundError('Task not found: {}'.format(task_name))
    
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
                    ),
                )

            # Override the option in the task config
            task_config['options'][name] = value

    task_config = TaskConfig(task_config)
    exception = None

    # Create and run the task
    try:
        task = task_class(config.project_config, task_config, org_config = org_config)
    except TaskRequiresSalesforceOrg as e:
        exception = click.UsageError('This task requires a salesforce org.  Use org default <name> to set a default org or pass the org name with the --org option')
    except TaskOptionsError as e:
        exception = click.UsageError(e.message)
    except Exception as e:
        if debug:
            import pdb
            import traceback
            traceback.print_exc()
            pdb.post_mortem()
        else:
            handle_sentry_event(config, no_prompt)
            raise
            
    if debug_before:
        import pdb 
        pdb.set_trace()

    if not exception:
        try:
            task()
        except TaskOptionsError as e:
            exception = click.UsageError(e.message)
        except ApexTestException as e:
            exception = click.ClickException('Failed: ApexTestFailure')
        except MetadataComponentFailure as e:
            exception = click.ClickException('Failed: MetadataComponentFailure')
        except MetadataApiError as e:
            exception = click.ClickException('Failed: MetadataApiError')
        except ScratchOrgException as e:
            exception = click.ClickException('ScratchOrgException: {}'.format(e.message))
        except Exception as e:
            if debug:
                import pdb
                import traceback
                traceback.print_exc()
                pdb.post_mortem()
            else:
                handle_sentry_event(config, no_prompt)
                raise

    # Save the org config in case it was modified in the task
    if org and org_config:
        config.keychain.set_org(org, org_config)

    if debug_after:
        import pdb
        pdb.set_trace()


    if exception:
        handle_sentry_event(config, no_prompt)
        raise exception


# Add the task commands to the task group
task.add_command(task_doc)
task.add_command(task_info)
task.add_command(task_list)
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
    flow = getattr(config.project_config, 'flows__{}'.format(flow_name))
    if not flow:
        raise FlowNotFoundError('Flow not found: {}'.format(flow_name))
    click.echo(pretty_dict(flow))

@click.command(name='run', help="Runs a flow")
@click.argument('flow_name')
@click.option('--org', help="Specify the target org.  By default, runs against the current default org")
@click.option('--delete-org', is_flag=True, help="If set, deletes the scratch org after the flow completes")
@click.option('--debug', is_flag=True, help="Drops into pdb, the Python debugger, on an exception")
@click.option('-o', nargs=2, multiple=True, help="Pass task specific options for the task as '-o taskname__option value'.  You can specify more than one option by using -o more than once.")
@click.option('--skip', multiple=True, help="Specify task names that should be skipped in the flow.  Specify multiple by repeating the --skip option")
@click.option('--no-prompt', is_flag=True, help="Disables all prompts.  Set for non-interactive mode use such as calling from scripts or CI systems")
@pass_config
def flow_run(config, flow_name, org, delete_org, debug, o, skip, no_prompt):
    # Check environment
    check_keychain(config)

    # Get necessary configs
    if org:
        org_config = config.project_config.get_org(org)
    else:
        org, org_config = config.project_config.keychain.get_default_org()

    if delete_org and not org_config.scratch:
        raise click.UsageError('--delete-org can only be used with a scratch org')

    flow = getattr(config.project_config, 'flows__{}'.format(flow_name))
    if not flow:
        raise FlowNotFoundError('Flow not found: {}'.format(flow_name))
    flow_config = FlowConfig(flow)
    if not flow_config.config:
        raise click.UsageError('No configuration found for flow {}'.format(flow_name))

    # Get the class to look up options
    class_path = flow_config.config.get('class_path', 'cumulusci.core.flows.BaseFlow')
    flow_class = import_class(class_path)

    exception = None

    # Parse command line options and add to task config
    options = {}
    if o:
        for option in o:
            options[option[0]] = option[1]

    # Create the flow and handle initialization exceptions
    try:
        flow = flow_class(config.project_config, flow_config, org_config, options, skip)
    except TaskRequiresSalesforceOrg as e:
        exception = click.UsageError('This flow requires a salesforce org.  Use org default <name> to set a default org or pass the org name with the --org option')
    except TaskOptionsError as e:
        exception = click.UsageError(e.message)
    except Exception as e:
        if debug:
            import pdb
            import traceback
            traceback.print_exc()
            pdb.post_mortem()
        else:
            raise

    if not exception:
        # Run the flow and handle exceptions
        try:
            flow()
        except TaskOptionsError as e:
            exception = click.UsageError(e.message)
        except ApexTestException as e:
            exception = click.ClickException('Failed: ApexTestException')
        except MetadataComponentFailure as e:
            exception = click.ClickException('Failed: MetadataComponentFailure')
        except MetadataApiError as e:
            exception = click.ClickException('Failed: MetadataApiError')
        except ScratchOrgException as e:
            exception = click.ClickException('ScratchOrgException: {}'.format(e.message))
        except Exception as e:
            if debug:
                import pdb
                import traceback
                traceback.print_exc()
                pdb.post_mortem()
            else:
                handle_sentry_event(config, no_prompt)
                raise

    # Delete the scratch org if --delete-org was set
    if delete_org:
        try:
            org_config.delete_org()
        except Exception as e:
            click.echo('Scratch org deletion failed.  Ignoring the error below to complete the flow:')
            click.echo(e.message)

    # Save the org config in case it was modified in a task
    if org and org_config:
        config.keychain.set_org(org, org_config)

    if exception:
        handle_sentry_event(config, no_prompt)
        raise exception

flow.add_command(flow_list)
flow.add_command(flow_info)
flow.add_command(flow_run)

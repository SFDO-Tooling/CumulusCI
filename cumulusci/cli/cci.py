from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()
from builtins import str
from builtins import object
import json
import os
import sys
import webbrowser
import code
import yaml
import time

try:
    import anydbm as dbm
except ImportError:
    import dbm.ndbm as dbm

from contextlib import contextmanager
from shutil import copyfile

import click
import pkg_resources
import requests
from plaintable import Table
from rst2ansi import rst2ansi
from jinja2 import Environment
from jinja2 import PackageLoader

import cumulusci
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import YamlGlobalConfig
from cumulusci.core.config import YamlProjectConfig
from cumulusci.core.exceptions import ApexTestException
from cumulusci.core.exceptions import BrowserTestFailure
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import FlowNotFoundError
from cumulusci.core.exceptions import KeychainKeyNotFound
from cumulusci.core.exceptions import OrgNotFound
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
from cumulusci.cli.config import CliConfig
from cumulusci.utils import doc_task
from cumulusci.oauth.salesforce import CaptureSalesforceOAuth
from .logger import init_logger


@contextmanager
def dbm_cache():
    """
    context manager for accessing simple dbm cache
    located at ~/.cumlusci/cache.dbm
    """
    config_dir = os.path.join(
        os.path.expanduser('~'),
        YamlGlobalConfig.config_local_dir,
    )
        
    if not os.path.exists(config_dir):
        os.mkdir(config_dir)

    db = dbm.open(os.path.join(config_dir, 'cache.dbm'), 'c',)
    yield db
    db.close()


def get_installed_version():
    """ returns the version name (e.g. 2.0.0b58) that is installed """
    req = pkg_resources.Requirement.parse('cumulusci')
    dist = pkg_resources.WorkingSet().find(req)
    return pkg_resources.parse_version(dist.version)


def get_latest_version():
    """ return the latest version of cumulusci in pypi, be defensive """
    # use the pypi json api https://wiki.python.org/moin/PyPIJSON
    res = requests.get('https://pypi.org/pypi/cumulusci/json', timeout=5).json()
    with dbm_cache() as cache:
        cache['cumulusci-latest-timestamp'] = str(time.time())
    return pkg_resources.parse_version(res['info']['version'])


def get_org(config, org_name=None):
    if org_name:
        org_config = config.keychain.get_org(org_name)
    else:
        org_name, org_config = config.project_config.keychain.get_default_org()
        if not org_config:
            raise click.UsageError('No org specified and no default org set.')
    return org_name, org_config


def check_latest_version():
    """ checks for the latest version of cumulusci from pypi, max once per hour """
    check = True

    with dbm_cache() as cache:
        if 'cumulusci-latest-timestamp' in cache:
            delta = time.time() - float(cache['cumulusci-latest-timestamp'])
            check = delta > 3600

    if check:
        result = get_latest_version() > get_installed_version()
        click.echo('Checking the version!')
        if result:
            click.echo(
                "An update to CumulusCI is available. Use pip install --upgrade cumulusci to update.")

def check_org_expired(config, org_name, org_config):
    if org_config.scratch and org_config.date_created and org_config.expired:
        click.echo(click.style('The scratch org is expired', fg='yellow'))
        if click.confirm('Attempt to recreate the scratch org?', default=True):
            config.keychain.create_scratch_org(
                org_name,
                org_config.config_name,
                org_config.days,
            )
            click.echo('Org config was refreshed, attempting to recreate scratch org')
            org_config = config.keychain.get_org(org_name)
            org_config.create_org()
        else:
            raise click.ClickException('The target scratch org is expired.  You can use cci org remove {} to remove the org and then recreate the config manually'.format(org_name))

    return org_config

def handle_exception_debug(config, debug, e, throw_exception=None, no_prompt=None):
    if debug:
        import pdb
        import traceback
        traceback.print_exc()
        pdb.post_mortem()
    else:
        if throw_exception:
            raise throw_exception
        else:
            handle_sentry_event(config, no_prompt)
            raise

def render_recursive(data, indent=None):
    if indent is None:
        indent = 0
    indent_str = ' ' * indent
    if isinstance(data, list):
        for item in data:
            render_recursive(item, indent=indent+4)
    elif isinstance(data, dict):
        for key, value in data.items():
            key_str = click.style(unicode(key) + ':', bold=True)
            if isinstance(value, list):
                render_recursive(value, indent=indent+4)
            elif isinstance(value, dict):
                click.echo('{}{}'.format(indent_str, key_str))
                render_recursive(value, indent=indent+4)
            else:
                click.echo('{}{} {}'.format(indent_str, key_str, value))

def check_org_overwrite(config, org_name):
    try:
        org = config.keychain.get_org(org_name)
        if org.scratch:
            if org.created:
                raise click.ClickException('Scratch org has already been created. Use `cci org scratch_delete {}`'.format(org_name))
        else:
            raise click.ClickException(
                'Org {} already exists.  Use `cci org remove` to delete it.'.format(org_name)
            )
    except OrgNotFound:
        pass
    return True

def make_pass_instance_decorator(obj, ensure=False):
    """Given an object type this creates a decorator that will work
    similar to :func:`pass_obj` but instead of passing the object of the
    current context, it will inject the passed object instance.

    This generates a decorator that works roughly like this::
        from functools import update_wrapper
        def decorator(f):
            @pass_context
            def new_func(ctx, *args, **kwargs):
                return ctx.invoke(f, obj, *args, **kwargs)
            return update_wrapper(new_func, f)
        return decorator
    :param obj: the object instance to pass.
    """
    def decorator(f):
        def new_func(*args, **kwargs):
            ctx = click.get_current_context()
            return ctx.invoke(f, obj, *args[1:], **kwargs)
        return click.decorators.update_wrapper(new_func, f)
    return decorator

try:
    check_latest_version()
except requests.exceptions.RequestException as e:
    click.echo('Error checking cci version:')
    click.echo(e.message) 

try:
    CLI_CONFIG = CliConfig()
except click.UsageError as e:
    click.echo(e.message)
    sys.exit(1)

pass_config = make_pass_instance_decorator(CLI_CONFIG)

def check_keychain(config):
    check_project_config(config)
    if config.project_config.keychain and config.project_config.keychain.encrypted and not config.keychain_key:
        raise click.UsageError(
            'You must set the environment variable CUMULUSCI_KEY with the encryption key to be used for storing org credentials')


def check_project_config(config):
    if not config.project_config:
        raise click.UsageError(
            'No project configuration found.  You can use the "project init" command to initilize the project for use with CumulusCI')


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
    click.echo(
        'An error event was recorded in sentry.io and can be viewed at the url:\n{}'.format(event_url))

    if not no_prompt and click.confirm(click.style('Do you want to open a browser to view the error in sentry.io?', bold=True)):
        webbrowser.open(event_url)

# Root command


@click.group('main')
@pass_config
def main(config):
    pass


@click.command(name='version', help='Print the current version of CumulusCI')
def version():
    click.echo(cumulusci.__version__)


@click.command(name='shell', help='Drop into a python shell')
@pass_config
@click.pass_context
def shell(ctx, config):
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


@click.group('service', help="Commands for connecting services to the keychain")
@pass_config
def service(config):
    pass

main.add_command(project)
main.add_command(org)
main.add_command(task)
main.add_command(flow)
main.add_command(version)
main.add_command(shell)
main.add_command(service)

# Commands for group: project


@click.command(name='init',
               help="Initialize a new project for use with the cumulusci toolbelt",
               )
@click.option('--extend', help="If set to the url of another Github repository configured for CumulusCI, creates this project as an extension which depends on the other Github project and all its dependencies")
@pass_config
def project_init(config, extend):
    if not os.path.isdir('.git'):
        raise click.ClickException("You are not in the root of a Git repository")

    if os.path.isfile('cumulusci.yml'):
        raise click.ClickException("This project already has a cumulusci.yml file")

    context = {}

    # Prep jinja2 environment for rendering files
    env = Environment(
        loader = PackageLoader('cumulusci', os.path.join('files', 'templates', 'project')),
        trim_blocks = True,
        lstrip_blocks = True,
    )

    # Project and Package Info
    click.echo()
    click.echo(click.style('# Project Info', bold=True, fg='blue'))
    click.echo('The following prompts will collect general information about the project')

    project_name = os.path.split(os.getcwd())[-1:][0]
    click.echo()
    click.echo('Enter the project name.  The name is usually the same as your repository name.  NOTE: Do not use spaces in the project name!')
    context['project_name'] = click.prompt(click.style('Project Name', bold=True), default=project_name)

    click.echo()
    click.echo("CumulusCI uses an unmanaged package as a container for your project's metadata.  Enter the name of the package you want to use.")
    context['package_name'] = click.prompt(click.style('Package Name', bold=True), default=project_name)

    click.echo()
    context['package_namespace'] = None
    if click.confirm(click.style("Is this a managed package project?", bold=True), default=False):
        click.echo('Enter the namespace assigned to the managed package for this project')
        context['package_namespace'] = click.prompt(click.style('Package Namespace', bold=True), default=project_name)

    click.echo()
    context['api_version'] = click.prompt(click.style('Salesforce API Version', bold=True), default=config.global_config.project__package__api_version)

    # Dependencies
    dependencies = []
    click.echo(click.style('# Extend Project', bold=True, fg='blue'))
    click.echo("CumulusCI makes it easy to build extensions of other projects configured for CumulusCI like Salesforce.org's NPSP and HEDA.  If you are building an extension of another project using CumulusCI and have access to its Github repository, use this section to configure this project as an extension.")
    if click.confirm(click.style("Are you extending another CumulusCI project such as NPSP or HEDA?", bold=True), default=False):
        click.echo("Please select from the following options:")
        click.echo("  1: HEDA (https://github.com/SalesforceFoundation/HEDAP)")
        click.echo("  2: NPSP (https://github.com/SalesforceFoundation/Cumulus)")
        click.echo("  3: Github URL (provide a URL to a Github repository configured for CumulusCI)")
        selection = click.prompt(click.style('Enter your selection', bold=True))
        if selection == '1':
            dependencies.append({'type': 'github', 'url': 'https://github.com/SalesforceFoundation/HEDAP'})
        elif selection == '2':
            dependencies.append({'type': 'github', 'url': 'https://github.com/SalesforceFoundation/Cumulus'})
        else:
            print(selection)
            github_url = click.prompt(click.style('Enter the Github Repository URL', bold=True))
            dependencies.append({'type': 'github', 'url': github_url})
    context['dependencies'] = dependencies

    # Git Configuration
    git_config = {}
    click.echo()
    click.echo(click.style('# Git Configuration', bold=True, fg='blue'))
    click.echo('CumulusCI assumes your default branch is master, your feature branches are named feature/*, your beta release tags are named beta/*, and your release tags are release/*.  If you want to use a different branch/tag naming scheme, you can configure the overrides here.  Otherwise, just accept the defaults.')

    git_default_branch = click.prompt(click.style('Default Branch', bold=True), default='master')
    if git_default_branch and git_default_branch != config.global_config.project__git__default_branch:
        git_config['default_branch'] = git_default_branch

    git_prefix_feature = click.prompt(click.style('Feature Branch Prefix', bold=True), default='feature/')
    if git_prefix_feature and git_prefix_feature != config.global_config.project__git__prefix_feature:
        git_config['prefix_feature'] = git_prefix_feature

    git_prefix_beta = click.prompt(click.style('Beta Tag Prefix', bold=True), default='beta/')
    if git_prefix_beta and git_prefix_beta != config.global_config.project__git__prefix_beta:
        git_config['prefix_beta'] = git_prefix_beta

    git_prefix_release = click.prompt(click.style('Release Tag Prefix', bold=True), default='release/')
    if git_prefix_release and git_prefix_release != config.global_config.project__git__prefix_release:
        git_config['prefix_release'] = git_prefix_release

    context['git'] = git_config

    #     test:
    test_config = []
    click.echo()
    click.echo(click.style('# Apex Tests Configuration', bold=True, fg='blue'))
    click.echo('The CumulusCI Apex test runner uses a SOQL where clause to select which tests to run.  Enter the SOQL pattern to use to match test class names.')
    
    test_name_match = click.prompt(click.style('Test Name Match', bold=True), default=config.global_config.project__test__name_match)
    if test_name_match and test_name_match == config.global_config.project__test__name_match:
        test_name_match = None
    context['test_name_match'] = test_name_match

    # Render the cumulusci.yml file
    template = env.get_template('cumulusci.yml')
    with open('cumulusci.yml','w') as f:
        f.write(template.render(**context))
    
    # Create src directory
    if not os.path.isdir('src'):
        os.mkdir('src')

    # Create sfdx-project.json
    if not os.path.isfile('sfdx-project.json'):

        sfdx_project = {
            "packageDirectories": [
                {
                    "path": "force-app",
                    "default": True,
                }
            ],
            "namespace": context['package_namespace'],
            "sourceApiVersion": context['api_version'],
        }
        with open('sfdx-project.json','w') as f:
            f.write(json.dumps(sfdx_project))
    
    # Create orgs subdir
    if not os.path.isdir('orgs'):
        os.mkdir('orgs')
      
    org_content_url = 'https://raw.githubusercontent.com/SalesforceFoundation/sfdo-package-cookiecutter/master/%7B%7Bcookiecutter.project_name%7D%7D/orgs/{}.json' 
    template = env.get_template('scratch_def.json')
    with open(os.path.join('orgs', 'beta.json'), 'w') as f:
        f.write(template.render(
            package_name = context['package_name'],
            org_name = 'Beta Test Org',
            edition = 'Developer',
        ))
    with open(os.path.join('orgs', 'dev.json'), 'w') as f:
        f.write(template.render(
            package_name = context['package_name'],
            org_name = 'Dev Org',
            edition = 'Developer',
        ))
    with open(os.path.join('orgs', 'feature.json'), 'w') as f:
        f.write(template.render(
            package_name = context['package_name'],
            org_name = 'Feature Test Org',
            edition = 'Developer',
        ))
    with open(os.path.join('orgs', 'release.json'), 'w') as f:
        f.write(template.render(
            package_name = context['package_name'],
            org_name = 'Release Test Org',
            edition = 'Enterprise',
        ))
   
    # Create initial create_contact.robot test 
    if not os.path.isdir('tests'):
        os.mkdir('tests')
        test_folder = os.path.join('tests','standard_objects')
        os.mkdir(test_folder)
        test_src = os.path.join(
            cumulusci.__location__,
            'robotframework',
            'tests',
            'salesforce',
            'create_contact.robot',
        )
        test_dest = os.path.join(
            test_folder,
            'create_contact.robot',
        )
        copyfile(test_src, test_dest)
        
    click.echo(click.style("Your project is now initialized for use with CumulusCI", bold=True, fg='green'))
    click.echo(click.style(
        "You can use the project edit command to edit the project's config file", fg='yellow'
    ))


@click.command(name='info', help="Display information about the current project's configuration")
@pass_config
def project_info(config):
    check_project_config(config)
    click.echo(render_recursive(config.project_config.project))


@click.command(name="dependencies", help="Displays the current dependencies for the project.  If the dependencies section has references to other github repositories, the repositories are inspected and a static list of dependencies is created")
@pass_config
def project_dependencies(config):
    check_project_config(config)
    dependencies = config.project_config.get_static_dependencies()
    for line in config.project_config.pretty_dependencies(dependencies):
        if ' headers:' in line:
            continue
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
# project.add_command(project_list)
# project.add_command(project_cd)

# Commands for group: service


@click.command(name='list', help='List services available for configuration and use')
@pass_config
def service_list(config):
    headers = ['service', 'description', 'is_configured']
    data = []
    for serv, schema in list(config.project_config.services.items()):
        is_configured = ''
        if serv in config.keychain.list_services():
            is_configured = '* '
        data.append((serv, schema['description'], is_configured))
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

        attributes = iter(list(getattr(
            config.project_config,
            'services__{0}__attributes'.format(name)
        ).items()))
        params = [self._build_param(attr, cnfg) for attr, cnfg in attributes]
        params.append(click.Option(('--project',), is_flag=True))

        @click.pass_context
        def callback(ctx, project=False, *args, **kwargs):
            check_keychain(config)
            serv_conf = dict((k, v) for k, v in list(kwargs.items())
                             if v != None)  # remove None values
            config.keychain.set_service(
                name, ServiceConfig(serv_conf), project)
            if project:
                click.echo(
                    '{0} is now configured for this project'.format(name))
            else:
                click.echo('{0} is now configured for global use'.format(name))

        ret = click.Command(name, params=params, callback=callback)
        return ret


@click.command(cls=ConnectServiceCommand, name='connect', help='Connect a CumulusCI task service')
@click.pass_context
def service_connect(ctx, *args, **kvargs):
    pass


@click.command(name='show', help='Show the details of a connected service')
@click.argument('service_name')
@pass_config
def service_show(config, service_name):
    check_keychain(config)
    try:
        service_config = config.keychain.get_service(service_name)
        click.echo(render_recursive(service_config.config))
    except ServiceNotConfigured:
        click.echo('{0} is not configured for this project.  Use service connect {0} to configure.'.format(
            service_name))

service.add_command(service_connect)
service.add_command(service_list)
service.add_command(service_show)

# Commands for group: org


@click.command(name='browser', help="Opens a browser window and logs into the org using the stored OAuth credentials")
@click.argument('org_name', required=False)
@pass_config
def org_browser(config, org_name):

    org_name, org_config = get_org(config, org_name)
    org_config = check_org_expired(config, org_name, org_config)

    try:
        org_config.refresh_oauth_token(config.keychain)
    except ScratchOrgException as e:
        raise click.ClickException('ScratchOrgException: {}'.format(e.message))

    webbrowser.open(org_config.start_url)

    # Save the org config in case it was modified
    config.keychain.set_org(org_config)


@click.command(name='connect', help="Connects a new org's credentials using OAuth Web Flow")
@click.argument('org_name')
@click.option('--sandbox', is_flag=True, help="If set, connects to a Salesforce sandbox org")
@click.option('--login-url', help='If set, login to this hostname.', default='https://login.salesforce.com')
@click.option('--default', is_flag=True, help='If set, sets the connected org as the new default org')
@click.option('--global-org', help='Set True if org should be used by any project', is_flag=True)
@pass_config
def org_connect(config, org_name, sandbox, login_url, default, global_org):
    check_org_overwrite(config, org_name)

    try:
        connected_app = config.keychain.get_service('connected_app')
    except ServiceNotConfigured as e:
        raise ServiceNotConfigured(
            'Connected App is required but not configured. ' +
            'Configure the Connected App service:\n' +
            'http://cumulusci.readthedocs.io/en/latest/' +
            'tutorial.html#configuring-the-project-s-connected-app'
        )
    if sandbox:
        login_url = 'https://test.salesforce.com'

    oauth_capture = CaptureSalesforceOAuth(
        client_id=connected_app.client_id,
        client_secret=connected_app.client_secret,
        callback_url=connected_app.callback_url,
        auth_site=login_url,
        scope='web full refresh_token'
    )
    oauth_dict = oauth_capture()
    org_config = OrgConfig(oauth_dict, org_name)
    org_config.load_userinfo()

    config.keychain.set_org(org_config, global_org)

    if default:
        org = config.keychain.set_default_org(org_name)
        click.echo('{} is now the default org'.format(org_name))


@click.command(name='default', help="Sets an org as the default org for tasks and flows")
@click.argument('org_name')
@click.option('--unset', is_flag=True, help="Unset the org as the default org leaving no default org selected")
@pass_config
def org_default(config, org_name, unset):

    if unset:
        org = config.keychain.unset_default_org()
        click.echo(
            '{} is no longer the default org.  No default org set.'.format(org_name))
    else:
        org = config.keychain.set_default_org(org_name)
        click.echo('{} is now the default org'.format(org_name))


@click.command(name='info', help="Display information for a connected org")
@click.argument('org_name', required=False)
@click.option('print_json', '--json', is_flag=True, help="Print as JSON")
@pass_config
def org_info(config, org_name, print_json):

    org_name, org_config = get_org(config, org_name)
    org_config = check_org_expired(config, org_name, org_config)

    try:
        org_config.refresh_oauth_token(config.keychain)
    except ScratchOrgException as e:
        raise click.ClickException('ScratchOrgException: {}'.format(e.message))

    if print_json:
        click.echo(json.dumps(org_config.config, sort_keys=True, indent=4))
    else:
        click.echo(render_recursive(org_config.config))

    if org_config.scratch and org_config.expires:
        click.echo('Org expires on {:%c}'.format(org_config.expires))
        
    # Save the org config in case it was modified
    config.keychain.set_org(org_config)


@click.command(name='list', help="Lists the connected orgs for the current project")
@pass_config
def org_list(config):
    data = []
    headers = ['org', 'default', 'scratch', 'days', 'expired', 'config_name', 'username']
    for org in config.project_config.list_orgs():
        org_config = config.project_config.get_org(org)
        row = [org]
        row.append('*' if org_config.default else '')
        row.append('*' if org_config.scratch else '')
        if org_config.days_alive:
            row.append('{} of {}'.format(org_config.days_alive, org_config.days) if org_config.scratch else '')
        else:
            row.append(org_config.days if org_config.scratch else '')
        row.append('*' if org_config.scratch and org_config.expired else '')
        row.append(org_config.config_name if org_config.config_name else '')
        username = org_config.config.get('username', org_config.userinfo__preferred_username)
        row.append(username if username else '')
        data.append(row)
    table = Table(data, headers)
    click.echo(table)

@click.command(name='remove', help="Removes an org from the keychain")
@click.argument('org_name')
@click.option('--global-org', is_flag=True, help="Set this option to force remove a global org.  Default behavior is to error if you attempt to delete a global org.")
@pass_config
def org_remove(config, org_name, global_org):

    try:
        org_config = config.keychain.get_org(org_name)
        if isinstance(org_config, ScratchOrgConfig):
            if org_config.date_created:
                # attempt to delete the org
                try:
                    click.echo("A scratch org was already created, attempting to delete...")
                    org_config.delete_org()
                except Exception as e:
                    click.echo("Deleting scratch org failed with error:")
                    click.echo(e)
    except OrgNotFound:
        raise click.ClickException('Org {} does not exist in the keychain'.format(org_name))
    config.keychain.remove_org(org_name, global_org)

@click.command(name='scratch', help="Connects a Salesforce DX Scratch Org to the keychain")
@click.argument('config_name')
@click.argument('org_name')
@click.option('--default', is_flag=True, help='If set, sets the connected org as the new default org')
@click.option('--delete', is_flag=True, help="If set, triggers a deletion of the current scratch org.  This can be used to reset the org as the org configuration remains to regenerate the org on the next task run.")
@click.option('--devhub', help="If provided, overrides the devhub used to create the scratch org")
@click.option('--days', help="If provided, overrides the scratch config default days value for how many days the scratch org should persist")
@click.option('--no-password', is_flag=True, help="If set, don't set a password for the org")
@pass_config
def org_scratch(config, config_name, org_name, default, delete, devhub, days, no_password):
    check_org_overwrite(config, org_name)

    scratch_configs = getattr(config.project_config, 'orgs__scratch')
    if not scratch_configs:
        raise click.UsageError('No scratch org configs found in cumulusci.yml')
    scratch_config = scratch_configs.get(config_name)
    if not scratch_config:
        raise click.UsageError(
            'No scratch org config named {} found in the cumulusci.yml file'.format(
                config_name)
        )

    if devhub:
        scratch_config['devhub'] = devhub

    config.keychain.create_scratch_org(
        org_name,
        config_name,
        days,
        set_password=not(no_password),
    )

    if default:
        org = config.keychain.set_default_org(org_name)
        click.echo('{} is now the default org'.format(org_name))


@click.command(name='scratch_delete', help="Deletes a Salesforce DX Scratch Org leaving the config in the keychain for regeneration")
@click.argument('org_name')
@pass_config
def org_scratch_delete(config, org_name):
    org_config = config.keychain.get_org(org_name)
    if not org_config.scratch:
        raise click.UsageError('Org {} is not a scratch org'.format(org_name))

    try:
        org_config.delete_org()
    except ScratchOrgException as e:
        exception = click.UsageError(e.message)

    config.keychain.set_org(org_config)


org.add_command(org_browser)
org.add_command(org_connect)
org.add_command(org_default)
org.add_command(org_info)
org.add_command(org_list)
org.add_command(org_remove)
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

    for name, options in list(config_src.tasks.items()):
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
    doc = doc_task(task_name, task_config).encode()
    click.echo(rst2ansi(doc))


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
    if org_config:
        org_config = check_org_expired(config, org, org_config)
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
        task = task_class(config.project_config,
                          task_config, org_config=org_config)
    except TaskRequiresSalesforceOrg as e:
        exception = click.UsageError(
            'This task requires a salesforce org.  Use org default <name> to set a default org or pass the org name with the --org option')
    except TaskOptionsError as e:
        exception = click.UsageError(e.message)
        handle_exception_debug(config, debug, e, throw_exception=exception)
    except Exception as e:
        handle_exception_debug(config, debug, e, no_prompt=no_prompt)

    if debug_before:
        import pdb
        pdb.set_trace()

    if not exception:
        try:
            task()
        except TaskOptionsError as e:
            exception = click.UsageError(e.message)
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except ApexTestException as e:
            exception = click.ClickException('Failed: ApexTestFailure')
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except BrowserTestFailure as e:
            exception = click.ClickException('Failed: BrowserTestFailure')
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except MetadataComponentFailure as e:
            exception = click.ClickException(
                'Failed: MetadataComponentFailure'
            )
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except MetadataApiError as e:
            exception = click.ClickException('Failed: MetadataApiError')
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except ScratchOrgException as e:
            exception = click.ClickException(
                'ScratchOrgException: {}'.format(e.message))
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except Exception as e:
            handle_exception_debug(config, debug, e, no_prompt=no_prompt)

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
        description = getattr(config.project_config,
                              'flows__{}__description'.format(flow))
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
    click.echo(render_recursive(flow))


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
        if not org_config:
            raise click.UsageError(
                '`cci flow run` requires an org.'
                ' No org was specified and default org is not set.'
            )

    org_config = check_org_expired(config, org, org_config)
    
    if delete_org and not org_config.scratch:
        raise click.UsageError(
            '--delete-org can only be used with a scratch org')

    flow = getattr(config.project_config, 'flows__{}'.format(flow_name))
    if not flow:
        raise FlowNotFoundError('Flow not found: {}'.format(flow_name))
    flow_config = FlowConfig(flow)
    if not flow_config.config:
        raise click.UsageError(
            'No configuration found for flow {}'.format(flow_name))

    # Get the class to look up options
    class_path = flow_config.config.get(
        'class_path', 'cumulusci.core.flows.BaseFlow')
    flow_class = import_class(class_path)

    exception = None

    # Parse command line options and add to task config
    options = {}
    if o:
        for option in o:
            options[option[0]] = option[1]

    # Create the flow and handle initialization exceptions
    try:
        flow = flow_class(config.project_config, flow_config,
                          org_config, options, skip, name=flow_name)
    except TaskRequiresSalesforceOrg as e:
        exception = click.UsageError(
            'This flow requires a salesforce org.  Use org default <name> to set a default org or pass the org name with the --org option')
    except TaskOptionsError as e:
        exception = click.UsageError(e.message)
        handle_exception_debug(config, debug, e, throw_exception=exception)
    except Exception as e:
        handle_exception_debug(config, debug, e, no_prompt=no_prompt)

    if not exception:
        # Run the flow and handle exceptions
        try:
            flow()
        except TaskOptionsError as e:
            exception = click.UsageError(e.message)
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except ApexTestException as e:
            exception = click.ClickException('Failed: ApexTestException')
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except BrowserTestFailure as e:
            exception = click.ClickException('Failed: BrowserTestFailure')
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except MetadataComponentFailure as e:
            exception = click.ClickException(
                'Failed: MetadataComponentFailure'
            )
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except MetadataApiError as e:
            exception = click.ClickException('Failed: MetadataApiError')
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except ScratchOrgException as e:
            exception = click.ClickException(
                'ScratchOrgException: {}'.format(e.message)
            )
            handle_exception_debug(config, debug, e, throw_exception=exception)
        except Exception as e:
            handle_exception_debug(config, debug, e, no_prompt=no_prompt)

    # Delete the scratch org if --delete-org was set
    if delete_org:
        try:
            org_config.delete_org()
        except Exception as e:
            click.echo(
                'Scratch org deletion failed.  Ignoring the error below to complete the flow:')
            click.echo(e.message)

    if exception:
        handle_sentry_event(config, no_prompt)
        raise exception

flow.add_command(flow_list)
flow.add_command(flow_info)
flow.add_command(flow_run)

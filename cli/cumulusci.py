import click
import json
import os
import sarge
import sys

# Exceptions
class AntTargetException(Exception):
    pass

class DeploymentException(Exception):
    pass

class ApexTestException(Exception):
    pass

class SalesforceCredentialsException(Exception):
    pass

def check_salesforce_credentials(env):
    missing = []
    if not env.get('SF_USERNAME'):
        missing.append('SF_USERNAME')
    if not env.get('SF_PASSWORD'):
        missing.append('SF_PASSWORD')
    if missing:
        raise SalesforceCredentialsException('You must set the environment variables: %s' % ', '.join(missing))

# Config object
class Config(object):
    def __init__(self):
        self.cumulusci_path = os.environ.get('CUMULUSCI_PATH', None)
        self.sf_username = os.environ.get('SF_USERNAME', None)
        self.sf_password = os.environ.get('SF_PASSWORD', None)
        self.sf_serverurl = os.environ.get('SF_SERVERURL', 'https://login.salesforce.com')
        self.oauth_client_id = os.environ.get('OAUTH_CLIENT_ID')
        self.oauth_client_secret = os.environ.get('OAUTH_CLIENT_SECRET')
        self.oauth_callback_url = os.environ.get('OAUTH_CALLBACK_URL')
        self.oauth_instance_url = os.environ.get('INSTANCE_URL')
        self.oauth_refresh_token = os.environ.get('REFRESH_TOKEN')
        self.advanced_testing = True
        self.debug_tests = os.environ.get('DEBUG_TESTS') not in [None, 'true', 'True']
        self.apex_logdir = 'apex_debug_logs'
        self.junit_output = 'test_results_junit.xml'
        self.json_output = 'test_results.json'
        self.parse_cumulusci_properties()
        self.branch = None
        self.commit = None
        self.build_type = None

    def parse_cumulusci_properties(self):
        if os.path.isfile('cumulusci.properties'):
            f = open('cumulusci.properties', 'r')
            for line in f:
                parts = line.split('=')
                attr = parts[0].strip().replace('.','__')
                value = parts[1].strip()
                setattr(self, attr, value)

    @property
    def test_mode(self):
        if self.advanced_testing:
            return 'parallel'
        return 'mdapi'

# Create a decorator to pass config around between commands
pass_config = click.make_pass_decorator(Config, ensure=True)

@click.group()
@pass_config
def cli(config):
    pass

@click.group(help="Commands to make building on CI servers easier")
@pass_config
def ci(config):
    pass

def get_build_info():
    # Attempt to parse out common ways of passing the branch
    branch = None
    commit = None
    vendor = None
    build_type = None
    # Solano CI
    if os.environ.get('TDDIUM'):
        branch = os.environ.get('TDDIUM_CURRENT_BRANCH')
        commit = os.environ.get('TDDIUM_CURRENT_COMMIT')
        vendor = 'SolanoCI'
    # Codeship
    # Jenkins
    # CicleCI
    if os.environ.get('CIRCLECI'):
        branch = os.environ.get('CIRCLE_BRANCH')
        commit = os.environ.get('CIRCLE_COMMIT')
    # Drone.io
    # Semaphore
    # Shippable
    # Fallback to calling git command line?

    if not branch or not commit:
        click.echo('FAIL: Could not determine branch or commit')
        return 1

    if branch.startswith('feature/'):
        build_type = 'feature'

    elif branch == 'master':
        build_type = 'master'

    click.echo("Detected %s build of branch %s at commit %s on %s" % (build_type, branch, commit, vendor))

    return branch, commit, build_type, vendor

# command: ci build_router
@click.command(help="Controls the initial routing of a build to its first step and executes the step")
@pass_config
def build_router(config):
    """ Routes a build commit to the proper type of initial build """

    branch, commit, build_type, vendor = get_build_info()

    if build_type == 'feature':
        click.echo('-- Building with feature branch flow')
        config.build_type = 'feature'
        config.branch = branch
        config.commit = branch
        config.sf_username = os.environ.get('SF_USERNAME_FEATURE')
        config.sf_password = os.environ.get('SF_PASSWORD_FEATURE')
        config.sf_serverurl = os.environ.get('SF_SERVERURL_FEATURE', config.sf_serverurl)
        unmanaged_deploy.main(args=['--run-tests','--full-delete'], standalone_mode=False, obj=config)

    elif build_type == 'master':
        click.echo('-- Building with master branch flow')
        config.build_type = 'master'
        config.branch = branch
        config.commit = branch
        config.sf_username = os.environ.get('SF_USERNAME_PACKAGING')
        config.sf_password = os.environ.get('SF_PASSWORD_PACKAGING')
        config.sf_serverurl = os.environ.get('SF_SERVERURL_PACKAGING', config.sf_serverurl)
        package_deploy.main(args=[], standalone_mode=False, obj=config)

# command: ci next_step
@click.command(help='A command to calculate and return the next steps for a ci build to run')
@pass_config
def next_step(config):
    step = None

    branch, commit, build_type, vendor = get_build_info()
    
    # SolanoCI
    if vendor == 'SolanoCI':
        profile = os.environ.get('SOLANO_PROFILE_NAME')
        version = None
        if profile:
            if profile == 'build_router' and branch == 'master':
                step = 'package_beta'
            elif profile == 'package_beta':
                f = open('package.properties', 'r')
                for line in f:
                    if line.startswith('PACKAGE_VERSION='):
                        version = line.replace('PACKAGE_VERSION=','')
                        break 
                step = 'deploy_beta_package'
                
        click.echo('Writing next step %s to solano-plan-variables.json' % step)
        f = open('solano-plan-variables.json', 'w')
        data = {'next_profile': step, 'version': version}
        f.write(json.dumps(data))
        return
         

@click.group()
@pass_config
def dev(config):
    pass

# Methods used to map config properties to environment variables for various scripts
def get_env_cumulusci(config):
    env = {
        'CUMULUSCI_PATH': config.cumulusci_path,
    }
    return env
    
def get_env_sf_org(config):
    return {
        'SF_USERNAME': config.sf_username,
        'SF_PASSWORD': config.sf_password,
        'SF_SERVERURL': config.sf_serverurl,
    }

def get_env_sf_org_oauth(config):
    return {
        'OAUTH_CLIENT_ID': config.oauth_client_id,
        'OAUTH_CLIENT_SECRET': config.oauth_client_secret,
        'OAUTH_CALLBACK_URL': config.oauth_callback_url,
        'INSTANCE_URL': config.oauth_instance_url,
        'REFRESH_TOKEN': config.oauth_refresh_token,
    }

def get_env_apex_tests(config):
    return {
        'TEST_MODE': config.test_mode,
        'DEBUG_TESTS': str(config.debug_tests),
        'DEBUG_LOGDIR': config.apex_logdir,
        'TEST_JSON_OUTPUT': config.json_output,
        'TEST_JUNIT_OUTPUT': config.junit_output,
    }
def get_env_github(config):
    return {
    }
   
def run_ant_target(target, env, config, check_credentials=None): 
    if check_credentials:
        try:
            check_salesforce_credentials(env)
        except SalesforceCredentialsException as e:
            click.echo('BUILD FAILED: %s' % e)
            sys.exit(4)
        
    # Execute the command
    p = sarge.Command('%s/ci/ant_wrapper.sh %s' % (config.cumulusci_path, target), stdout=sarge.Capture(buffer_size=-1), env=env)
    p.run(async=True)

    # Print the stdout buffer until the command completes and capture all lines in log for reference in exceptions
    log = []
    while p.returncode is None:
        for line in p.stdout:
            log.append(line.rstrip())
            click.echo(line.rstrip())
        p.poll()

    # Check the return code, raise the appropriate exception if needed
    if p.returncode:
        logtxt = '\n'.join(log)
        try:
            if logtxt.find('All Component Failures:') != -1:
                raise DeploymentException(logtxt)
            elif logtxt.find('[exec] Failing Tests') != -1:
                raise ApexTestException(logtxt)
            else:
                raise AntTargetException(logtxt)
        except DeploymentException as e:
            click.echo('BUILD FAILED: One or more deployment errors occurred')
            sys.exit(2)
        except ApexTestException as e:
            click.echo('BUILD FAILED: One or more Apex tests failed')
            sys.exit(3)
        except AntTargetException as e:
            click.echo('BUILD FAILED: One or more Ant target errors occurred')
            sys.exit(1)
    return p

def check_required_env(env, required_env):
    missing = []
    for key in required_env:
        if key not in env or not env[key]:
            missing.append(key)
    if missing:
        raise click.BadParameter('You must set the environment variables: %s' % ', '.join(missing))

def run_python_script(script, env, config, required_env=None): 
    if required_env:
        check_required_env(env, required_env)

    # Execute the command
    p = sarge.Command('python %s/ci/%s' % (config.cumulusci_path, script), stdout=sarge.Capture(buffer_size=-1), env=env)
    p.run(async=True)

    # Print the stdout buffer until the command completes and capture all lines in log for reference in exceptions
    log = []
    while p.returncode is None:
        for line in p.stdout:
            log.append(line.rstrip())
            click.echo(line.rstrip())
        p.poll()

    return p
        
# command: dev unmanaged_deploy
@click.command(
    help='Runs a full deployment of the code including unused stale package metadata, setting up dependencies, deploying the code, and optionally running tests',
    context_settings={'color': True},
)
@click.option('--run-tests', default=False, is_flag=True, help='If set, run tests as part of the deployment.  Defaults to not running tests')
@click.option('--full-delete', default=False, is_flag=True, help='If set, delete all package metadata at the start of the build instead of doing an incremental delete.  **WARNING**: This deletes all package metadata, use with caution.  This option can be necessary if you have reference issues during an incremental delete deployment.')
@click.option('--ee-org', default=False, is_flag=True, help='If set, use the deployUnmanagedEE target which prepares the code for loading into a production Enterprise Edition org.  Defaults to False.')
@click.option('--deploy-only', default=False, is_flag=True, help='If set, runs only the deployWithoutTest target.  Does not clean the org, update dependencies, or run any tests.  This option invalidates all other options')
@pass_config
def unmanaged_deploy(config, run_tests, full_delete, ee_org, deploy_only):

    # Determine the deploy target to use based on options
    target = None
    if deploy_only:
        target = 'deployWithoutTest'
    elif ee_org:
        target = 'deployUnmanagedEE'
        if run_tests:
            target += ' runAllTests'
    else:
        if run_tests:
            target = 'deployCI'
        else:
            target = 'deployDevOrg'

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_sf_org(config))
    env.update(get_env_apex_tests(config))

    # Set the delete mode
    if not deploy_only:
        env['UNMANAGED_DESTROY_MODE'] = 'incremental'
        if full_delete:
            env['UNMANAGED_DESTROY_MODE'] = 'full'
        click.echo('Metadata deletion mode: %s' % env['UNMANAGED_DESTROY_MODE'])

    # Run the command
    p = run_ant_target(target, env, config, check_credentials=True)

# command: package_deploy
@click.command(help='Runs a full deployment of the code as managed code to the packaging org including setting up dependencies, deleting metadata removed from the repository, deploying the code, and optionally running tests')
@pass_config
def package_deploy(config):
    # Determine the deploy target to use based on options
    target = 'deployCIPackageOrg'

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_sf_org(config))
    env.update(get_env_apex_tests(config))

    p = run_ant_target(target, env, config, check_credentials=True)

# command: package_beta
@click.command(help='Use Selenium to upload a package version in the packaging org')
@click.argument('commit')
@click.option('--build-name', default='Manual build from CumulusCI CLI', help='If provided, overrides the build name used to name the package version')
@click.option('--selenium-url', help='If provided, uses a Selenium Server at the specified url.  Example: http://127.0.0.1:4444/wd/hub')
@pass_config
def package_beta(config, commit, build_name, selenium_url):

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_sf_org_oauth(config))

    if config.cumulusci__package__name:
        env['PACKAGE'] = config.cumulusci__package__name
    env['BUILD_WORKSPACE'] = '.'
    env['BUILD_COMMIT'] = commit
    env['BUILD_NAME'] = build_name

    required_env = [
        'OAUTH_CLIENT_ID',
        'OAUTH_CLIENT_SECRET',
        'OAUTH_CALLBACK_URL',
        'INSTANCE_URL',
        'REFRESH_TOKEN',
        'PACKAGE',
        'BUILD_NAME',
        'BUILD_COMMIT',
        'BUILD_WORKSPACE',
    ]

    script = 'package_upload.py'
    if selenium_url:
        required_env.append('SELENIUM_URL')
        env['SELENIUM_URL'] = selenium_url
        script = 'package_upload_ss.py'

    p = run_python_script(script, env, config, required_env=required_env)

# command: packaging managed_deploy
@click.command(help='Installs a managed package version and optionally runs the tests from the installed managed package')
@click.option('--run-tests', default=False, help='If True, run tests as part of the deployment.  Defaults to False')
@click.option('--package-version', help='The package version number to install.  Examples: 1.2, 1.2.1, 1.3 (Beta 3)')
@click.option('--commit', help='The commit for the version.  This is used to look up dependencies from the version.properties file and unpackaged subdirectory in the repository')
@pass_config
def managed_deploy(config, run_tests, package_version, commit):
    # Determine the deploy target to use based on options
    target = 'deployManaged'
    if run_tests:
        target += ' runAllTestsManaged'

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_sf_org(config))
    env.update(get_env_apex_tests(config))

    env['PACKAGE_VERSION'] = package_version
    env['BUILD_COMMIT'] = commit

    p = run_ant_target(target, env, config, check_credentials=True)

# command: dev update_package_xml
@click.command(help='Updates the src/package.xml file by parsing out the metadata under src/')
@pass_config
def update_package_xml(config):
    env = get_env_cumulusci(config)
    p = run_ant_target('updatePackageXml', env, config)

@click.group()
@pass_config
def packaging(config):
    pass

@click.group()
@pass_config
def managed(config):
    pass

@click.group(help='Commands for interacting with the Github repository for the project')
@pass_config
def github(config):
    pass

@click.group(help='Commands for integrating builds with mrbelvedere (https://github.com/SalesforceFoundation/mrbelvedere)')
@pass_config
def mrbelvedere(config):
    pass

# Top level commands
cli.add_command(managed_deploy)
cli.add_command(package_deploy)
cli.add_command(package_beta)
cli.add_command(unmanaged_deploy)
cli.add_command(update_package_xml)

# Group: ci
ci.add_command(build_router)
ci.add_command(next_step)
cli.add_command(ci)

#cli.add_command(dev)
#cli.add_command(packaging)
#cli.add_command(managed)
cli.add_command(github)
cli.add_command(mrbelvedere)

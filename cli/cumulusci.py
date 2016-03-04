import click
import json
import os
import pprint
import sarge
import sys
from time import sleep

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
        # Default Build Info
        self.env_prefix = ''
        self.branch = None
        self.commit = None
        self.build_type = None
        self.build_vendor = None
        self.build_workspace = '.'
        self.steps_feature = ''
        self.steps_master = ''

        # Detected Build Info
        build_info = get_build_info()
        for key, value in build_info.items():
            setattr(self, key, value)

        self.steps_feature = os.environ.get(self.env_prefix + 'CUMULUSCI_STEPS_FEATURE', 'deploy').split(',')
        self.steps_master = os.environ.get(self.env_prefix + 'CUMULUSCI_STEPS_MASTER', 'deploy').split(',')
        self.cumulusci_path = os.environ.get(self.env_prefix + 'CUMULUSCI_PATH', None)

        # Salesforce org credentials
        self.sf_username = os.environ.get(self.env_prefix + 'SF_USERNAME', None)
        self.sf_password = os.environ.get(self.env_prefix + 'SF_PASSWORD', None)
        self.sf_serverurl = os.environ.get(self.env_prefix + 'SF_SERVERURL', 'https://login.salesforce.com')

        # OAuth credentials for the packaging org
        self.oauth_client_id = os.environ.get(self.env_prefix + 'OAUTH_CLIENT_ID')
        self.oauth_client_secret = os.environ.get(self.env_prefix + 'OAUTH_CLIENT_SECRET')
        self.oauth_callback_url = os.environ.get(self.env_prefix + 'OAUTH_CALLBACK_URL')
        self.oauth_instance_url = os.environ.get(self.env_prefix + 'INSTANCE_URL')
        self.oauth_refresh_token = os.environ.get(self.env_prefix + 'REFRESH_TOKEN')

        # Github Credentials
        self.github_org_name = os.environ.get(self.env_prefix + 'GITHUB_ORG_NAME')
        self.github_repo_name = os.environ.get(self.env_prefix + 'GITHUB_REPO_NAME')
        self.github_username = os.environ.get(self.env_prefix + 'GITHUB_USERNAME')
        self.github_password = os.environ.get(self.env_prefix + 'GITHUB_PASSWORD')
    
        # Default test configuration and override via environment variable
        self.advanced_testing = True
        self.debug_tests = os.environ.get(self.env_prefix + 'DEBUG_TESTS') not in [None, 'true', 'True']
        self.apex_logdir = 'apex_debug_logs'
        self.junit_output = 'test_results_junit.xml'
        self.json_output = 'test_results.json'

        # Branch naming
        self.prefix_beta = os.environ.get(self.env_prefix + 'PREFIX_BETA', 'beta/')
        self.prefix_release = os.environ.get(self.env_prefix + 'PREFIX_RELEASE', 'release/')
        self.master_branch = os.environ.get(self.env_prefix + 'MASTER_BRANCH', 'master')

        # Org pooling support.  CI builds can pass the ORG_SUFFIX environment variable to use a different set of environment variables
        # for the Salesforce org credentials.
        self.feature_org_suffix = os.environ.get(self.env_prefix + 'FEATURE_ORG_SUFFIX', 'FEATURE')
        self.beta_org_suffix = os.environ.get(self.env_prefix + 'BETA_ORG_SUFFIX', 'BETA')

        # Parse the cumulusci.properties file if it exists.  Make all variables into attrs by replacing . with __ in the variable name
        self.parse_cumulusci_properties()

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
    info = {}
    # Solano CI
    if os.environ.get('TDDIUM'):
        info['branch'] = os.environ.get('TDDIUM_CURRENT_BRANCH')
        info['commit'] = os.environ.get('TDDIUM_CURRENT_COMMIT')
        info['build_vendor'] = 'SolanoCI'
    # Codeship
    # Jenkins
    # CicleCI
    elif os.environ.get('CIRCLECI'):
        info['branch'] = os.environ.get('CIRCLE_BRANCH')
        info['commit'] = os.environ.get('CIRCLE_COMMIT')
        info['build_vendor'] = 'CircleCI'
    # Drone.io
    # Semaphore
    # Shippable
    # Bamboo
    elif os.environ.get('bamboo_buildKey'):
        info['branch'] = os.environ.get('bamboo_repository_branch_name')
        info['commit'] = os.environ.get('bamboo_repository_revision_number')
        info['build_vendor'] = 'Bamboo'
        info['env_prefix'] = 'bamboo_'

    # Fallback to calling git command line?

    if info.get('branch') and info['branch'].startswith('feature/'):
        info['build_type'] = 'feature'

    elif info.get('branch') and info['branch'] == 'master':
        info['build_type'] = 'master'

    click.echo("Detected build information: %s" % pprint.pformat(info))

    return info

# command: ci deploy
@click.command(name='deploy', help="Determines the right kind of build for the branch and runs the build including tests")
@pass_config
def ci_deploy(config):
    if not config.commit or not config.branch:
        raise click.BadParameter('Could not determine commit or branch for ci deploy')
        
    if config.build_type == 'feature':
        click.echo('-- Building with feature branch flow against %s org' % config.feature_org_suffix)
        config.sf_username = os.environ.get(config.env_prefix + 'SF_USERNAME_' + config.feature_org_suffix)
        config.sf_password = os.environ.get(config.env_prefix + 'SF_PASSWORD_' + config.feature_org_suffix)
        config.sf_serverurl = os.environ.get(config.env_prefix + 'SF_SERVERURL_' + config.feature_org_suffix, config.sf_serverurl)
        deploy_unmanaged.main(args=['--run-tests','--full-delete'], standalone_mode=False, obj=config)

    elif config.build_type == 'master':
        click.echo('-- Building with master branch flow')
        config.sf_username = os.environ.get(config.env_prefix + 'SF_USERNAME_PACKAGING')
        config.sf_password = os.environ.get(config.env_prefix + 'SF_PASSWORD_PACKAGING')
        config.sf_serverurl = os.environ.get(config.env_prefix + 'SF_SERVERURL_PACKAGING', config.sf_serverurl)
        deploy_packaging.main(args=[], standalone_mode=False, obj=config)

# command: ci next_step
@click.command(help='A command to calculate and return the next steps for a ci build to run')
@pass_config
def next_step(config):
    step = 'dummy'

    # SolanoCI
    if config.build_vendor == 'SolanoCI':
        profile = os.environ.get('SOLANO_PROFILE_NAME')
        i_current_step = 0
        if profile:
            if config.build_type == 'feature':
                try:
                    i_current_step = config.steps_feature.index(profile)
                    if len(config.steps_feature) > i_current_step + 1:
                        step = config.steps_feature[i_current_step + 1]
                except ValueError:
                    pass
            elif config.build_type == 'master':
                try:
                    i_current_step = config.steps_master.index(profile)
                    if len(config.steps_master) > i_current_step + 1:
                        step = config.steps_master[i_current_step + 1]
                except ValueError:
                    pass
               
        # The first step is manually specified in the plan, so the first dynamic step starts at 2 
        step_var = 'plan_step_%s' % str(i_current_step + 2)

        click.echo('Writing next step %s as %s to solano-plan-variables.json' % (step, step_var))

        f = open('solano-plan-variables.json', 'w')
        data = {step_var: step}
        f.write(json.dumps(data))
        f.close()
        return
         
# command: ci beta_deploy
@click.command(help="Deploys a beta managed package version by its git tag and commit")
@click.argument('tag')
@click.argument('commit')
@click.option('--run-tests', default=False, is_flag=True, help='If set, run tests as part of the deployment.  Defaults to not running tests')
@click.option('--retries', default=3, help="The number of times the installation should retry installation if the prior attempt failed due to a package unavailable error.  This error is common after uploading a package if the test org is on a different pod.  There is a slight delay in copying newly uploaded packages.  Defaults to 3")
@pass_config
def beta_deploy(config, tag, commit, org, run_tests, retries):
    config.sf_username = os.environ.get(config.env_prefix + 'SF_USERNAME_' + config.beta_org_suffix)
    config.sf_password = os.environ.get(config.env_prefix + 'SF_PASSWORD_' + config.beta_org_suffix)
    config.sf_serverurl = os.environ.get(config.env_prefix + 'SF_SERVERURL_' + config.beta_org_suffix, config.sf_serverurl)

    package_version = tag.replace('beta/','').replace('-',' ').replace('Beta','(Beta').replace('_',' ') + ')'

    args = [config.commit, package_version]
    if run_tests:
        args.append('--run-tests')

    try:
        # Call the deploy_managed command to install the beta
        deploy_managed.main(args=args, standalone_mode=False, obj=config)

    except DeploymentException as e:
        # Get failure text for searching
        error = repr(e)

        # Only retry if there are retries and the version doesn't exist, raise all other exceptions
        if not retries or (error.find('Error: Invalid Package, Details: This package is not yet available') == -1 and error.find('Error: InstalledPackage version number : %s does not exist!' % package_version) == -1):
            raise e

        click.echo("Retrying installation of %s due to package unavailable error.  Sleeping for 1 minute before retrying installation.  %s retries remain" % (package_version, retries - 1))
        sleep(60)

        # Construct arguments for retry
        args = [
            tag,
            commit,
            '--org',
            org,
            '--retries',
            retries - 1,
        ]
        if run_tests:
            args.append('--runtests')

        click.echo("Retry command: cumulusci ci beta_deploy %s" % ' '.join(args))

        # Retry
        deploy_beta.main(args=args, standalone_mode=False)
        

@click.group(help="Commands useful to developers in interacting with Salesforce package source metadata")
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
        'GITHUB_ORG_NAME': config.github_org_name,
        'GITHUB_REPO_NAME': config.github_repo_name,
        'GITHUB_USERNAME': config.github_username,
        'GITHUB_PASSWORD': config.github_password,
    }
def get_env_build(config):
    return {
        'BUILD_WORKSPACE': config.build_workspace,
        'BUILD_COMMIT': config.commit,
    }
def get_env_apextestsdb(config):
    return {
        'APEXTESTSDB_BASE_URL': config.apextestsdb_base_url,
        'APEXTESTSDB_USER_ID': config.apextestsdb_user_id,
        'APEXTESTSDB_TOKEN': config.apextestsdb_token,
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
        
# command: dev deploy
@click.command(
    name='deploy',
    help='Runs a full deployment of the code including unused stale package metadata, setting up dependencies, deploying the code, and optionally running tests',
    context_settings={'color': True},
)
@click.option('--run-tests', default=False, is_flag=True, help='If set, run tests as part of the deployment.  Defaults to not running tests')
@click.option('--full-delete', default=False, is_flag=True, help='If set, delete all package metadata at the start of the build instead of doing an incremental delete.  **WARNING**: This deletes all package metadata, use with caution.  This option can be necessary if you have reference issues during an incremental delete deployment.')
@click.option('--ee-org', default=False, is_flag=True, help='If set, use the deployUnmanagedEE target which prepares the code for loading into a production Enterprise Edition org.  Defaults to False.')
@click.option('--deploy-only', default=False, is_flag=True, help='If set, runs only the deployWithoutTest target.  Does not clean the org, update dependencies, or run any tests.  This option invalidates all other options')
@pass_config
def deploy_unmanaged(config, run_tests, full_delete, ee_org, deploy_only):

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

# command: release deploy
@click.command(name='deploy', help='Runs a full deployment of the code as managed code to the packaging org including setting up dependencies, deleting metadata removed from the repository, deploying the code, and optionally running tests')
@pass_config
def deploy_packaging(config):
    # Determine the deploy target to use based on options
    target = 'deployCIPackageOrg'

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_sf_org(config))
    env.update(get_env_apex_tests(config))

    p = run_ant_target(target, env, config, check_credentials=True)

# command: release upload_beta
@click.command(help='Use Selenium to upload a package version in the packaging org')
@click.argument('commit')
@click.option('--build-name', default='Manual build from CumulusCI CLI', help='If provided, overrides the build name used to name the package version')
@click.option('--selenium-url', help='If provided, uses a Selenium Server at the specified url.  Example: http://127.0.0.1:4444/wd/hub')
@click.option('--create-release', is_flag=True, help='If set, creates a release in Github which also creates a tag')
@pass_config
def upload_beta(config, commit, build_name, selenium_url, create_release):

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_sf_org_oauth(config))
    env.update(get_env_build(config))

    if config.cumulusci__package__name:
        env['PACKAGE'] = config.cumulusci__package__name

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

    if create_release:
        # Parse package.properties
        version = None
        commit = None

        if os.path.isfile('package.properties'):
            f = open('package.properties', 'r')
            for line in f:
                line = line.strip()
                if line.startswith('PACKAGE_VERSION='):
                    version = line.replace('PACKAGE_VERSION=','')
                    continue
                if line.startswith('BUILD_COMMIT='):
                    commit = line.replace('BUILD_COMMIT=','')
                    continue

        # Call the github_release command
        click.echo('Creating release in Github for %s from commit %s' % (version, commit))
        github_release.main(args=[version, commit], standalone_mode=False, obj=config)

# command: run_tests
@click.command(help='Run Apex tests in the target org via the Tooling API and report results. Defaults to running all unmanaged test classes ending in _TEST.')
@click.option('--test-match', default="%_TEST", help="A SOQL like format value to match against the test name.  Defaults to %_TEST.  You can use commas to separate multiple values like %_SMOKE_TESTS,%_LOAD_TESTS")
@click.option('--test-exclude', help="Similar to --test-match, but adds exclusions to the test name matching.  Defaults to no value.  You can use commas to separate multiple values")
@click.option('--namespace', help="If set, only search for tests inside the specified namespace.  By default, all unmanaged tests are searched")
@click.option('--debug-logdir', help="A directory to store debug logs from each test class.  If specified, a TraceFlag is created which captures debug logs.  When all tests have completed, the debug logs are downloaded to the specified directory.  They are then parsed to capture detail information on the test.  See --json-output for more details")
@click.option('--json-output', help="If set, outputs test results data in json format to the specified file.  This option is most useful with the --debug-logs option.  The resulting json file contains detailed information on the code execution structure of each test method including cumulative limits usage both inside and outside the startTest/stopTest context")
@pass_config
def run_tests(config, test_match, test_exclude, namespace, debug_logdir, json_output):
    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_sf_org(config))

    env['APEX_TEST_NAME_MATCH'] = test_match
    if test_exclude:
        env['APEX_TEST_NAME_EXCLUDE'] = test_exclude
    if namespace:
        env['NAMESPACE'] = test_exclude
    if debug_logdir:
        env['DEBUG_TESTS'] = 'True'
        env['DEBUG_LOGDIR'] = debug_logdir

        # ensure the logdir actually exists
        if not os.path.exists(debug_logdir):
            os.makedirs(debug_logdir)
    if json_output:
        env['JSON_OUTPUT'] = json_output

    env['JUNIT_OUTPUT'] = config.junit_output

    required_env = [
        'SF_USERNAME',
        'SF_PASSWORD',
        'SF_SERVERURL',
        'APEX_TEST_NAME_MATCH',
    ]

    p = run_python_script('run_apex_tests.py', env, config, required_env=required_env)


# command: apextestsdb_upload
# FIXME: Use S3 storage to facilitate uploads of local test_results.json file
@click.command(help='Upload a test_results.json file to the ApexTestsDB web application for analysis.  NOTE: This does not currently work with local files.  You will have to upload the file to an internet accessible web server and provide the path.')
@click.argument('execution_name')
@click.argument('results_file_url')
@click.option('--repo-url', help="Set to override the repository url for the report")
@click.option('--branch', help="Set to override the branch for the report")
@click.option('--commit', help="Set to override the commit sha for the report")
@click.option('--execution-url', help="Set to provide a link back to execution results")
@click.option('--environment', help="Set a custom name for the build environment")
def apextestsdb_upload(config, execution_name, results_file_url, repo_url, branch, commit, execution_url, environment):
    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_apextestsdb(config))
    env.update(get_env_build(config))

    env['PACKAGE_VERSION'] = version
    env['PREFIX_BETA'] = config.prefix_beta

    env['REPOSITORY_URL'] = repository_url
    env['BRANCH'] = branch
    env['COMMIT_SHA'] = commit
    env['EXECUTION_NAME'] = execution_name
    env['EXECUTION_URL'] = execution_url
    env['ENVIRONMENT'] = environment

    required_env = [
        'APEXTESTSDB_BASE_URL',
        'APEXTESTSDB_USER_ID',
        'APEXTESTSDB_TOKEN',
        'REPOSITORY_URL',
        'BRANCH_NAME',
        'COMMIT_SHA',
        'EXECUTION_NAME',
        'EXECUTION_URL',
        'ENVIRONMENT',
    ]

    p = run_python_script('upload_test_results.py', env, config, required_env=required_env)


# command: github release
@click.command(name='release', help='Create a release in Github')
@click.argument('version')
@click.argument('commit')
@pass_config
def github_release(config, version, commit):

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_github(config))
    env.update(get_env_build(config))

    env['PACKAGE_VERSION'] = version
    env['PREFIX_BETA'] = config.prefix_beta

    required_env = [
        'GITHUB_ORG_NAME',
        'GITHUB_REPO_NAME',
        'GITHUB_USERNAME',
        'GITHUB_PASSWORD',
        'BUILD_COMMIT',
        'PACKAGE_VERSION',
        'BUILD_WORKSPACE',
        'PREFIX_BETA',
    ]

    p = run_python_script('github/create_release.py', env, config, required_env=required_env)

# command: github release_notes
@click.command(name='release_notes', help='Generates release notes by parsing Warning, Info, and Issues headings from pull request bodies of all pull requests merged since the last production release tag')
@click.argument('tag')
@click.option('--last-tag', help="Instead of looking for the last tag, you can manually provide it.  This is useful if you skip a release and want to build release notes going back 2 releases")
@click.option('--update-release', is_flag=True, help="If set, add the release notes to the body")
@pass_config
def github_release_notes(config, tag, last_tag, update_release):

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_github(config))

    env['CURRENT_REL_TAG'] = tag
    if last_tag:
        env['LAST_REL_TAG'] = last_tag
    env['MASTER_BRANCH'] = config.master_branch
    env['PREFIX_BETA'] = config.prefix_beta
    env['PREFIX_RELEASE'] = config.prefix_release
    env['PRINT_ONLY'] = str(not update_release)

    required_env = [
        'GITHUB_ORG_NAME',
        'GITHUB_REPO_NAME',
        'GITHUB_USERNAME',
        'GITHUB_PASSWORD',
        'CURRENT_REL_TAG',
        'MASTER_BRANCH',
        'PREFIX_BETA',
        'PREFIX_RELEASE',
    ]

    p = run_python_script('github/release_notes.py', env, config, required_env=required_env)

# command: github master_to_feature
@click.command(name='master_to_feature', help='Attempts to merge a commit on the master branch to all open feature branches.  Creates pull requests assigned to the developer of the feature branch if a merge conflict occurs.')
@click.option('--commit', help="By default, the head commit on master will be merged.  You can override this behavior by specifying a commit sha")
@pass_config
def github_master_to_feature(config, commit):

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_github(config))

    if commit:
        env['BUILD_COMMIT'] = commit
    env['MASTER_BRANCH'] = config.master_branch

    required_env = [
        'GITHUB_ORG_NAME',
        'GITHUB_REPO_NAME',
        'GITHUB_USERNAME',
        'GITHUB_PASSWORD',
        'MASTER_BRANCH',
    ]

    p = run_python_script('github/merge_master_to_feature.py', env, config, required_env=required_env)

# command: github clone_tag
@click.command(name='clone_tag', help='Create one tag referencing the same commit as another tag')
@click.argument('src_tag')
@click.argument('tag')
@pass_config
def github_clone_tag(config, src_tag, tag):

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_github(config))

    env['SRC_TAG'] = src_tag
    env['TAG'] = tag

    required_env = [
        'GITHUB_ORG_NAME',
        'GITHUB_REPO_NAME',
        'GITHUB_USERNAME',
        'GITHUB_PASSWORD',
        'SRC_TAG',
        'TAG',
    ]

    p = run_python_script('github/tag_to_tag.py', env, config, required_env=required_env)

# command: dev deploy_managed
@click.command(help='Installs a managed package version and optionally runs the tests from the installed managed package')
@click.argument('commit')
@click.argument('package_version')
@click.option('--run-tests', is_flag=True, help='If True, run tests as part of the deployment.  Defaults to False')
@pass_config
def deploy_managed(config, commit, package_version, run_tests):
    # Determine the deploy target to use based on options
    target = 'deployManaged'
    if package_version.find('(Beta ') != -1:
        target = 'deployManagedBeta'
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

@click.group(help="Commands used in the release process and interacting with a Manage Package packing org")
@pass_config
def release(config):
    pass

@click.group(help='Commands for interacting with the Github repository for the project')
@pass_config
def github(config):
    pass

# Top level commands

# Group: ci
ci.add_command(ci_deploy)
ci.add_command(next_step)
ci.add_command(beta_deploy)
cli.add_command(ci)

# Group: dev
dev.add_command(apextestsdb_upload)
dev.add_command(deploy_unmanaged)
dev.add_command(deploy_managed)
dev.add_command(run_tests)
dev.add_command(update_package_xml)
cli.add_command(dev)

# Group: release
release.add_command(deploy_packaging)
release.add_command(upload_beta)
cli.add_command(release)

# Group: github
github.add_command(github_clone_tag)
github.add_command(github_master_to_feature)
github.add_command(github_release)
github.add_command(github_release_notes)
cli.add_command(github)

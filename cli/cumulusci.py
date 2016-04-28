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
    # The following environment variables should be considered sensitive and masked if needed by the build vendor
    # For example, Bamboo only masks variables with 'PASSWORD' in their name.  Thus, with Bamboo, all variables would
    # have _PASSWORD appended to their names to ensure masking
    masked_vars = (
        'OAUTH_CLIENT_ID',
        'OAUTH_CLIENT_SECRET',
        'OAUTH_CALLBACK_URL',
        'INSTANCE_URL',
        'REFRESH_TOKEN',
        'MRBELVEDERE_PACKAGE_KEY',
    )
    def __init__(self):
        # Default Build Info
        self.env_prefix = None
        self.env_mask = None
        self.branch = None
        self.commit = None
        self.build_id = None
        self.build_url = None
        self.build_type = None
        self.build_vendor = None
        self.build_workspace = '.'
        self.steps_feature = ''
        self.steps_master = ''

        # Detected Build Info
        build_info = get_build_info()
        for key, value in build_info.items():
            setattr(self, key, value)

        self.steps_feature = self.get_env_var('CUMULUSCI_STEPS_FEATURE', 'deploy').split(',')
        self.steps_master = self.get_env_var('CUMULUSCI_STEPS_MASTER', 'deploy').split(',')
        self.cumulusci_path = self.get_env_var('CUMULUSCI_PATH', None)

        # Salesforce org credentials
        self.sf_username = self.get_env_var('SF_USERNAME', None)
        self.sf_password = self.get_env_var('SF_PASSWORD', None)
        self.sf_serverurl = self.get_env_var('SF_SERVERURL', 'https://login.salesforce.com')

        # OAuth credentials for the packaging org
        self.oauth_client_id = self.get_env_var('OAUTH_CLIENT_ID')
        self.oauth_client_secret = self.get_env_var('OAUTH_CLIENT_SECRET')
        self.oauth_callback_url = self.get_env_var('OAUTH_CALLBACK_URL')
        self.oauth_instance_url = self.get_env_var('INSTANCE_URL')
        self.oauth_refresh_token = self.get_env_var('REFRESH_TOKEN')

        # Github Credentials
        self.github_org_name = self.get_env_var('GITHUB_ORG_NAME')
        self.github_repo_name = self.get_env_var('GITHUB_REPO_NAME')
        self.github_username = self.get_env_var('GITHUB_USERNAME')
        self.github_password = self.get_env_var('GITHUB_PASSWORD')
    
        # Default test configuration and override via environment variable
        self.advanced_testing = True
        self.debug_tests = self.get_env_var('DEBUG_TESTS') not in [None, 'true', 'True']
        self.apex_logdir = 'apex_debug_logs'
        self.junit_output = 'test_results_junit.xml'
        self.json_output = 'test_results.json'

        # Branch and tag naming
        self.prefix_feature = self.get_env_var('PREFIX_FEATURE', 'feature/')
        self.prefix_beta = self.get_env_var('PREFIX_BETA', 'beta/')
        self.prefix_release = self.get_env_var('PREFIX_RELEASE', 'release/')
        self.master_branch = self.get_env_var('MASTER_BRANCH', 'master')

        # Org pooling support.  CI builds can pass the ORG_SUFFIX environment variable to use a different set of environment variables
        # for the Salesforce org credentials.
        self.feature_org_suffix = self.get_env_var('FEATURE_ORG_SUFFIX', 'FEATURE')
        self.beta_org_suffix = self.get_env_var('BETA_ORG_SUFFIX', 'BETA')

        # Parse the cumulusci.properties file if it exists.  Make all variables into attrs by replacing . with __ in the variable name
        self.parse_cumulusci_properties()

        # mrbelvedere configuration
        self.mrbelvedere_base_url = self.get_env_var('MRBELVEDERE_BASE_URL')
        self.mrbelvedere_package_key = self.get_env_var('MRBELVEDERE_PACKAGE_KEY')

        # Calculated values
        self.build_type = self.get_build_type()
        self.tag_message = self.get_tag_message()


    def get_build_type(self):
        # Determine the build type
        build_type = self.get_env_var('BUILD_TYPE')
        if not build_type:
            if self.branch and self.branch.startswith(self.prefix_feature):
                build_type = 'feature'
            elif self.branch and self.branch == self.master_branch:
                build_type = 'master'
        return build_type

    def get_tag_message(self):
        # Determine the tag message.  This is used as a key to find tags created by the current build

        # We only have a tag message on master builds
        if not self.build_type == 'master':
            return None

        message = ['Tag created by',]

        if self.build_id:
            message.append('build %s' % self.build_id) 
        else:
            message.append('CumulusCI master flow build')

        if self.build_vendor:
            message.append('on %s' % self.build_vendor) 

        return ' '.join(message)

    def get_env_var(self, var, default=None):
        var_name = var
        if self.env_prefix:
            var_name = self.env_prefix + var_name
        if self.env_mask and var in self.masked_vars:
            var_name = var_name + self.env_mask

        return os.environ.get(var_name, default)

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

        # Bamboo sets the build id and url variables to be unique to the job but we're interested
        # in the plan level build id and url.  Thus, we parse out the job portion to get the plan values
        job_key = os.environ.get('bamboo_shortJobKey')  # ex: JOB1
        job_build_key = os.environ.get('bamboo_buildResultKey') # ex: REPO-PLAN1-JOB1-123

        build_id = job_build_key
        build_id = build_id.replace('-%s-' % job_key, '-') # ex: REPO-PLAN1-123
        build_url = os.environ.get('bamboo_buildResultsUrl') # ex: https://your_bamboo_url/builds/browse/REPO-PLAN1-JOB1-123
        build_url = build_url.replace(job_build_key, build_id) # ex: https://your_bamboo_url/builds/browse/REPO-PLAN1-123
        
        info['build_id'] = build_id
        info['build_url'] = build_url
        info['env_prefix'] = 'bamboo_'
        info['env_mask'] = '_PASSWORD'

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
        config.sf_username = config.get_env_var('SF_USERNAME_' + config.feature_org_suffix)
        config.sf_password = config.get_env_var('SF_PASSWORD_' + config.feature_org_suffix)
        config.sf_serverurl = config.get_env_var('SF_SERVERURL_' + config.feature_org_suffix, config.sf_serverurl)
        deploy_unmanaged.main(args=['--run-tests','--full-delete'], standalone_mode=False, obj=config)

    elif config.build_type == 'master':
        click.echo('-- Building with master branch flow')
        config.sf_username = config.get_env_var('SF_USERNAME_PACKAGING')
        config.sf_password = config.get_env_var('SF_PASSWORD_PACKAGING')
        config.sf_serverurl = config.get_env_var('SF_SERVERURL_PACKAGING', config.sf_serverurl)
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
def beta_deploy(config, tag, commit, run_tests, retries):
    config.sf_username = config.get_env_var('SF_USERNAME_' + config.beta_org_suffix)
    config.sf_password = config.get_env_var('SF_PASSWORD_' + config.beta_org_suffix)
    config.sf_serverurl = config.get_env_var('SF_SERVERURL_' + config.beta_org_suffix, config.sf_serverurl)

    click.echo("Building as user %s" % config.sf_username)

    # FIXME: This hard codes the beta tag prefix
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
        'PATH': os.environ.get('PATH'),
    }
    venv = os.environ.get('VIRTUAL_ENV')
    if venv:
        env['VIRTUAL_ENV'] = venv
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
def get_env_mrbelvedere(config):
    return {
        'MRBELVEDERE_BASE_URL': config.mrbelvedere_base_url,
        'MRBELVEDERE_PACKAGE_KEY': config.mrbelvedere_package_key,
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
@click.option('--package', help='By default, the package name will be parsed from the cumulusci.properties file in the repo.  Use the package option to override the package name.')
@pass_config
def upload_beta(config, commit, build_name, selenium_url, create_release, package):

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_sf_org_oauth(config))
    env.update(get_env_build(config))

    if package:
        env['PACKAGE'] = package
    elif hasattr(config, 'cumulusci__package__name__managed'):
        env['PACKAGE'] = config.cumulusci__package__name__managed
    elif hasattr(config, 'cumulusci__package__name'):
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


# command: github commit_status
@click.command(name='commit_status', help='Set the Github Commit Status for the current commit.  Acceptible state values are pending, success, error, and failure')
@click.argument('state')
@click.option('--context', help="The context of this status.  This is usually a string to identify a build system")
@click.option('--url', help="A url to the build.  This is usually a link to a build system that ran the build")
@click.option('--description', help="Override the default status description text")
@click.option('--commit', help="By default, the current local commit is used.  You can pass a commit sha here to set status on a different commit")
@pass_config
def github_commit_status(config, state, context, url, description, commit):

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_github(config))
    env.update(get_env_build(config))

    env['STATE'] = state

    if context:
        env['CONTEXT'] = context
    elif config.build_vendor:
        # Set context to build vendor if it exists
        env['CONTEXT'] = config.build_vendor

    if url:
        env['BUILD_URL'] = url

    if description:
        env['DESCRIPTION'] = description

    if commit:
        env['BUILD_COMMIT'] = commit
    elif config.commit:
        env['BUILD_COMMIT'] = config.commit

    required_env = [
        'GITHUB_ORG_NAME',
        'GITHUB_REPO_NAME',
        'GITHUB_USERNAME',
        'GITHUB_PASSWORD',
        'STATE',
        'BUILD_COMMIT',
    ]

    p = run_python_script('github/set_commit_status.py', env, config, required_env=required_env)

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

    env['BUILD_COMMIT'] = commit
    env['PACKAGE_VERSION'] = version
    env['PREFIX_BETA'] = config.prefix_beta
    if config.tag_message:
        env['MESSAGE'] = config.tag_message

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

# command: mrbelvedere release
@click.command(name='release', help='Adds a new beta or production release to an existing package in mrbelvedere, sets up dependencies for the installer, and sets the version as the latest beta or production')
@click.argument('version')
@click.option('--namespace', help='By default, the cumulusci.package.namespace property from cumulusci.properties will be used.  This option allows you to override the namespace for the package in mrbelvedere if needed')
@pass_config
def mrbelvedere_release(config, version, namespace):

    # Build the environment for the command
    env = get_env_cumulusci(config)
    env.update(get_env_mrbelvedere(config))

    env['PACKAGE_VERSION'] = version
    env['PROPERITIES_PATH'] = 'version.properties'
    if namespace:
        env['NAMESPACE'] = namespace
    else:
        env['NAMESPACE'] = config.cumulusci__package__namespace

    # Determine if this is a production or beta version
    if version.find('Beta') != -1:
        env['BETA'] = 'True'

    required_env = [
        'MRBELVEDERE_BASE_URL',
        'MRBELVEDERE_PACKAGE_KEY',
        'NAMESPACE',
    ]

    p = run_python_script('mrbelvedere_update_dependencies.py', env, config, required_env=required_env)


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

@click.group(help='Commands for interacting with mrbelvedere')
@pass_config
def mrbelvedere(config):
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
github.add_command(github_commit_status)
github.add_command(github_master_to_feature)
github.add_command(github_release)
github.add_command(github_release_notes)
cli.add_command(github)

# Group: mrbelvedere
mrbelvedere.add_command(mrbelvedere_release)
cli.add_command(mrbelvedere)

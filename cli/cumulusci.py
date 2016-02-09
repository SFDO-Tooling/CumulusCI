import click
import os
import sarge

OPTION_ARGS = {
    'advanced_testing': {
        'default': True,
        'help': 'Set to False to fallback to using the Force.com Ant Migration Tool for running tests.  Default is True which uses the Tooling API based test runner that can run tests in parallel, capture and parse debug logs, and output JUnit format test results',
    },
    'debug_tests': {
        'default': False,
        'help': 'If set to True, debug logs will be captured for all tests classes to provide extended output.  Defaults to False.'
    },
}

class Config(object):
    def __init__(self):
        self.cumulusci_path = os.environ.get('CUMULUSCI_PATH', None)
        self.sf_username = os.environ.get('SF_USERNAME', None)
        self.sf_password = os.environ.get('SF_PASSWORD', None)
        self.sf_serverurl = os.environ.get('SF_SERVERURL', 'https://login.salesforce.com')
        self.advanced_testing = True
        self.debug_tests = False
        self.apex_logdir = 'apex_debug_logs'
        self.junit_output = 'test_results_junit.xml'
        self.json_output = 'test_results.json'
        self.parse_cumulusci_properties

    def parse_cumulusci_properties(self):
        if os.path.isfile('cumulusci.properties'):
            f = open('cumulusci.properties', 'r')
            for line in f:
                parts = line.split('=')
                attr = parts[0].strip().replace('.','__')
                value = parts[1].strip()
                setattr(self, key, value)

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
def get_env_cum(config):
    return {
    }
   
def run_ant_target(target, env, config): 
    # Execute the command
    p = sarge.Command('%s/ci/ant_wrapper.sh %s' % (config.cumulusci_path, target), stdout=sarge.Capture(buffer_size=-1), env=env)
    p.run(async=True)
    while p.returncode is None:
        for line in p.stdout:
            click.echo(line.rstrip())
        p.poll()
    return p

@click.command(help='Runs a full deployment of the code including deleting package metadata from the target org (WARNING), setting up dependencies, deploying the code, and optionally running tests')
@click.option('--run-tests', default=False, help='If True, run tests as part of the deployment.  Defaults to False')
@click.option('--ee-org', default=False, help='If True, use the deployUnmanagedEE target which prepares the code for loading into a production Enterprise Edition org.  Defaults to False.')
@pass_config
def deploy(config, run_tests, ee_org):

    # Determine the deploy target to use based on options
    target = None
    if ee_org:
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

    p = run_ant_target(target, env, config)
    click.echo('Return Code = %s' % p.returncode)

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

@click.group()
@pass_config
def github(config):
    pass

@click.group()
@pass_config
def mrbelvedere(config):
    pass

dev.add_command(deploy)
dev.add_command(update_package_xml)

cli.add_command(dev)
cli.add_command(packaging)
cli.add_command(managed)
cli.add_command(github)
cli.add_command(mrbelvedere)

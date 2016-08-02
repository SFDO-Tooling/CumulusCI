import click

from core.config import YamlGlobalConfig
from core.config import YamlProjectConfig

class CliConfig(object):
    def __init__(self):
        self._init_global_config()
        self._init_project_config()

    def _init_global_config(self):
        self.global_config = YamlGlobalConfig()

    def _init_project_config(self):
        self.project_config = self.global_config.get_project_config()

pass_config = click.make_pass_decorator(CliConfig, ensure=True)

# Top Level Groups    
@click.group('cli')
@pass_config
def cli(config):
    pass

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

# Commands for group: org
@click.command(name='browser', help="Opens a browser window and logs into the org using the stored OAuth credentials")
@pass_config
def org_browser(config):
    pass

@click.command(name='connect', help="Connects a new org's credentials using OAuth Web Flow")
@pass_config
def org_connect(config):
    pass

@click.command(name='info', help="Display information for a connected org")
@pass_config
def org_info(config):
    pass

@click.command(name='list', help="Lists the connected orgs for the current project")
@pass_config
def org_list(config):
    pass

org.add_command(org_browser)
org.add_command(org_connect)
org.add_command(org_info)
org.add_command(org_list)

# Commands for group: task
@click.command(name='list', help="List available tasks for the current context")
@pass_config
def task_list(config):
    pass

@click.command(name='info', help="Displays information for a task")
@pass_config
def task_info(config):
    pass

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

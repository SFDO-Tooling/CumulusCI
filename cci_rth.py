""" run-time hook for pyinstaller """

import importlib

from cumulusci.cli.config import CliConfig
from cumulusci.cli.logger import init_logger

init_logger()

# import project-level modules
modules = set()
config = CliConfig()
for task_name, task in config.project_config.config['tasks'].iteritems():
    class_path = task['class_path'].split('.')
    if class_path[0] != 'cumulusci':
        modules.add('.'.join(class_path[:-1]))
for module in modules:
    importlib.import_module(module)

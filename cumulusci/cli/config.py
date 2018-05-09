import os
import sys
import click

from cumulusci.core.config import YamlGlobalConfig
from cumulusci.core.config import YamlProjectConfig
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import ProjectConfigNotFound
from cumulusci.core.utils import import_class
from .logger import init_logger


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
        except ConfigError as e:
            raise click.UsageError('Config Error: {}'.format(e.message))

    def _load_keychain(self):
        self.keychain_key = os.environ.get('CUMULUSCI_KEY')
        if self.project_config:
            keychain_class = os.environ.get(
                'CUMULUSCI_KEYCHAIN_CLASS',
                self.project_config.cumulusci__keychain,
            )
            self.keychain_class = import_class(keychain_class)
            self.keychain = self.keychain_class(
                self.project_config, self.keychain_key)
            self.project_config.set_keychain(self.keychain)


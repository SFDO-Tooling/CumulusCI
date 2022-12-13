import base64
import json
import os
import sys
import typing as T
from pathlib import Path
from shutil import rmtree

from cumulusci.core.config import OrgConfig, ScratchOrgConfig, ServiceConfig
from cumulusci.core.config.sfdx_org_config import SfdxOrgConfig
from cumulusci.core.exceptions import (
    ConfigError,
    CumulusCIException,
    CumulusCIUsageError,
    KeychainKeyNotFound,
    OrgCannotBeLoaded,
    OrgNotFound,
    ServiceNotConfigured,
)
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.keychain.base_project_keychain import DEFAULT_CONNECTED_APP_NAME
from cumulusci.core.keychain.serialization import (
    load_config_from_json_or_pickle,
    serialize_config_to_json_or_pickle,
)
from cumulusci.core.utils import import_class, import_global
from cumulusci.utils.encryption import _get_cipher, encrypt_and_b64
from cumulusci.utils.yaml.cumulusci_yml import ScratchOrg

DEFAULT_SERVICES_FILENAME = "DEFAULT_SERVICES.json"

# The file permissions that we want set on all
# .org and .service files. Equivalent to -rw-------
SERVICE_ORG_FILE_MODE = 0o600
OS_FILE_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
if sys.platform.startswith("win"):
    # O_BINARY only available on Windows
    OS_FILE_FLAGS |= os.O_BINARY

scratch_org_class = os.environ.get("CUMULUSCI_SCRATCH_ORG_CLASS")
if scratch_org_class:
    scratch_org_factory = import_global(scratch_org_class)  # pragma: no cover
else:
    scratch_org_factory = ScratchOrgConfig


"""
EncryptedFileProjectKeychain
----------------------------
This class represents a project keychain that stores services and orgs in encrypted
files. These files have the extensions: '.org' and '.service'.

Service files (.service) are organized under ~/.cumulusci/services/ into sub-directories that
pertain to a particular service type (e.g. github, connected_app). These files hold
the encrypted 'attributes' of each service as they are listed in the universal
cumulusci.yml file. There are multiple DEFAULT_SERVICES.json files that map a particular
service type to the default alias for that taype.

The DEFAULT_SERVICES.json file that resides at ~/.cumulusci holds the global default
services mappings. Each local project directory (~/.cumulusci/project/) also has a
DEFAULT_SERVICES.json file for any services that have been configured to be project specific.

Org files (.org) live in both under ~/.cumulusci and in local project directories.
The .org files store an encrypted access_token and other org attributes. There is a
DEFAULT_ORG.txt file in each local project directory that stores the name of
the default org for that project.
"""


class EncryptedFileProjectKeychain(BaseProjectKeychain):
    encrypted = True
    env_service_alias_prefix = "env"
    env_service_var_prefix = "CUMULUSCI_SERVICE_"
    env_org_var_prefix = "CUMULUSCI_ORG_"

    @property
    def global_config_dir(self):
        try:
            global_config_dir = (
                self.project_config.universal_config_obj.cumulusci_config_dir
            )
        except AttributeError:
            # Handle a global config passed as a project config
            global_config_dir = self.project_config.cumulusci_config_dir
        return global_config_dir

    @property
    def project_local_dir(self):
        return self.project_config.project_local_dir

    #######################################
    #             Encryption              #
    #######################################

    # TODO: Move this class into encryption.py
    def _decrypt_config(self, config_class, encrypted_config, extra=None, context=None):
        if self.key:
            if not encrypted_config:
                if extra:
                    return config_class(None, *extra)
                else:
                    return config_class()
            encrypted_config = base64.b64decode(encrypted_config)
            try:
                iv = encrypted_config[:16]
                cipher, iv = _get_cipher(self.key, iv=iv)
                pickled = cipher.decryptor().update(encrypted_config[16:])
                unpickled = load_config_from_json_or_pickle(pickled)
            except ValueError as e:
                message = "\n".join(
                    [
                        f"Unable to decrypt{' ' + context if context else ''}. \n"
                        "A changed CUMULUSCI_KEY or laptop password might be the cause.\n"
                        "Unfortunately, there is usually no way to recover an Org's Configuration \n"
                        "once this has happened.\n"
                        "Typically we advise users to delete the unusable file or rename it to .bak.\n"
                        "The org can be connected or imported again to replace the corrupted config.\n"
                        "(Specific error: " + str(e) + ")\n"
                    ]
                )
                raise KeychainKeyNotFound(message) from e

        config_dict = self.cleanup_Python_2_configs(unpickled)

        args = [config_dict]
        if extra:
            args += extra
        return self._construct_config(config_class, args)

    def cleanup_Python_2_configs(self, unpickled):
        # Convert bytes created in Python 2
        config_dict = {}

        # After a few months, we can clean up this code if nobody reports
        # warnings.
        message = (
            "Unexpected bytes found in config.\n"
            "Please inform the CumulusCI team.\n"
            "Future versions of CumulusCI may break your config."
        )
        for k, v in unpickled.items():
            if isinstance(k, bytes):
                self.logger.warning(message)
                k = k.decode("utf-8")
            if isinstance(v, bytes):
                self.logger.warning(message)
                v = v.decode("utf-8")
            config_dict[k] = v

        return config_dict

    def _construct_config(self, config_class, args):
        config = args[0]
        if config.get("scratch"):
            config_class = scratch_org_factory
        elif config.get("sfdx"):
            config_class = SfdxOrgConfig

        return config_class(*args)

    def _get_config_bytes(self, config) -> bytes:
        """Depending on if a key is present return
        the bytes that we want to store on the keychain."""
        org_bytes = None
        org_bytes = serialize_config_to_json_or_pickle(config.config, self.logger)

        if self.key:
            org_bytes = encrypt_and_b64(org_bytes, self.key)

        assert org_bytes is not None, "org_bytes should have a value"
        return org_bytes

    def _validate_key(self):
        # the key can be None when we detect issues using keyring
        if not self.key:
            return
        if len(self.key) != 16:
            raise ConfigError("The keychain key must be 16 characters long.")

    #######################################
    #               Orgs                  #
    #######################################

    def get_default_org(self):
        """Retrieve the name and configuration of the default org"""
        # first look for a file with the default org in it
        default_org_path = self._default_org_path
        if default_org_path and default_org_path.exists():
            org_name = default_org_path.read_text().strip()
            try:
                org_config = self.get_org(org_name)
                return org_name, org_config
            except OrgNotFound:  # org was deleted
                default_org_path.unlink()  # we don't really have a usable default anymore

        # fallback to old way of doing it
        org_name, org_config = super().get_default_org()
        if org_name:
            self.set_default_org(org_name)  # upgrade to new way
        return org_name, org_config

    def set_default_org(self, name: str):
        """Set the default org for tasks and flows by name"""
        super().set_default_org(name)
        self._default_org_path.write_text(name)

    def unset_default_org(self):
        """Unset the default orgs for tasks and flows"""
        super().unset_default_org()
        if self._default_org_path:
            try:
                self._default_org_path.unlink()
            except FileNotFoundError:
                pass

    @property
    def _default_org_path(self):
        if self.project_local_dir:
            return Path(self.project_local_dir) / "DEFAULT_ORG.txt"

    def _load_orgs(self) -> None:
        self._load_orgs_from_environment()
        self._load_org_files(self.global_config_dir, GlobalOrg)
        self._load_org_files(self.project_local_dir, LocalOrg)

    def _load_orgs_from_environment(self):
        for env_var_name, value in os.environ.items():
            if env_var_name.startswith(self.env_org_var_prefix):
                self._load_org_from_environment(env_var_name, value)

    def _load_org_from_environment(self, env_var_name, value):
        org_config = json.loads(value)
        org_name = env_var_name[len(self.env_org_var_prefix) :].lower()
        if org_config.get("scratch"):
            org_config = scratch_org_factory(
                json.loads(value), org_name, keychain=self, global_org=False
            )
        else:
            org_config = OrgConfig(
                org_config, org_name, keychain=self, global_org=False
            )

        self.set_org(org_config, global_org=False, save=False)

    def _load_org_files(self, dirname: str, constructor=None):
        """Loads .org files in a given directory onto the keychain"""
        if not dirname:
            return
        dir_path = Path(dirname)
        for item in sorted(dir_path.iterdir()):
            if item.suffix == ".org":
                with open(item, "rb") as f:
                    config = f.read()
                name = item.name.replace(".org", "")
                if "orgs" not in self.config:
                    self.config["orgs"] = {}
                self.config["orgs"][name] = (
                    constructor(config, filename=item) if constructor else config
                )

    def _set_org(self, org_config, global_org, save=True):
        if org_config.keychain:
            assert org_config.keychain is self
        assert org_config.global_org == global_org
        org_config.keychain = self
        org_config.global_org = global_org

        org_name = org_config.name

        org_bytes = self._get_config_bytes(org_config)
        assert isinstance(org_bytes, bytes)

        if global_org:
            org_config = GlobalOrg(org_bytes)
        else:
            org_config = LocalOrg(org_bytes)

        self.orgs[org_name] = org_config

        # if keychain is explicitly set to
        # EnvironmentProjectKeychain never save the org config.
        keychain_class = os.environ.get("CUMULUSCI_KEYCHAIN_CLASS")
        if keychain_class == "EnvironmentProjectKeychain":
            message = (
                "The keychain is currently set to EnvironmentProjectKeychain; "
                "skipping save of org config to file. "
                "If you would like orgs to be saved for re-use later, remove the "
                "CUMULUSCI_KEYCHAIN_CLASS environment variable."
            )
            self.logger.warning(message)
            return

        if save:
            self._save_org(
                org_name,
                org_config.data,
                global_org,
            )

    def _save_org(self, name, org_bytes, global_org):
        """
        @name - name of the org
        @org_bytes - bytes-like objecte to write to disk
        @global_org - whether or not this is a global org
        """
        if global_org:
            filename = Path(f"{self.global_config_dir}/{name}.org")
        elif self.project_local_dir is None:
            return
        else:
            filename = Path(f"{self.project_local_dir}/{name}.org")

        fd = os.open(filename, OS_FILE_FLAGS, SERVICE_ORG_FILE_MODE)
        with open(fd, "wb") as f:
            f.write(org_bytes)

    def _get_org(self, org_name: str) -> ScratchOrgConfig:
        try:
            config = self.orgs[org_name].data
            global_org = self.orgs[org_name].global_org
        except KeyError:
            raise OrgNotFound(f"Org with name '{org_name}' does not exist.")

        try:
            org = self._config_from_bytes(config, org_name)
        except Exception as e:
            try:
                filename = self.orgs[org_name].filename
            except Exception:  # pragma: no cover
                filename = None
            if not filename:
                raise e
            raise OrgCannotBeLoaded(
                f"Cannot parse config loaded from\n{filename}\n{e}\n"
            )
        org.global_org = global_org

        if isinstance(org, ScratchOrgConfig):
            self._merge_config_from_yml(org)

        return org

    def _merge_config_from_yml(self, scratch_config: ScratchOrgConfig):
        """Merges any values configurable via cumulusci.yml
        into the scratch org config that is loaded from file."""

        configurable_attributes = list(ScratchOrg.schema()["properties"].keys())
        for attr in configurable_attributes:
            try:
                value_from_yml = self.project_config.config["orgs"]["scratch"][
                    scratch_config.name
                ][attr]
                scratch_config.config[attr] = value_from_yml
            except KeyError:
                pass

    def _config_from_bytes(self, config, name):
        if self.key:
            org = self._decrypt_config(
                OrgConfig,
                config,
                extra=[name, self],
                context=f"org config ({name})",
            )
        else:
            config = load_config_from_json_or_pickle(config)
            org = self._construct_config(OrgConfig, [config, name, self])

        return org

    def _remove_org(self, name, global_org):
        scope = self.global_config_dir if global_org else self.project_local_dir
        org_path = Path(f"{scope}/{name}.org")
        if not org_path.exists():
            if not global_org:
                raise OrgNotFound(
                    f"Could not find org named {name} to delete.  Deleting in project org mode.  Is {name} a global org?"
                )
            raise OrgNotFound(
                f"Could not find org named {name} to delete.  Deleting in global org mode.  Is {name} a project org instead of a global org?"
            )

        org_path.unlink()
        del self.orgs[name]

    def cleanup_org_cache_dirs(self):
        """Cleanup directories that are not associated with a connected/live org."""

        if not self.project_config or not self.project_config.cache_dir:
            return
        active_org_domains = set()
        for org in self.list_orgs():
            org_config = self.get_org(org)
            domain = org_config.get_domain()
            if domain:
                active_org_domains.add(domain)

        assert self.project_config.cache_dir, "Project cache dir does not exist."
        assert self.global_config_dir, "Global config directory does not exist."

        project_org_directories = (self.project_config.cache_dir / "orginfo").glob("*")
        global_org_directories = (self.global_config_dir / "orginfo").glob("*")

        for path in list(project_org_directories) + list(global_org_directories):
            if path.is_dir() and path.name not in active_org_domains:
                rmtree(path)

    #######################################
    #              Services               #
    #######################################

    def set_default_service(
        self, service_type: str, alias: str, project: bool = False, save: bool = True
    ) -> None:
        """Public API for setting a default service e.g. `cci service default`

        @param service_type: the type of service
        @param alias: the name of the service
        @param project: Should this be a project default
        @param save: save the defaults so they are loaded on subsequent executions
        @raises ServiceNotConfigured if service_type or alias are invalid
        """
        self._validate_service_type_and_alias(service_type, alias)
        self._default_services[service_type] = alias
        if save:
            self._save_default_service(service_type, alias, project=project)

    def rename_service(
        self, service_type: str, current_alias: str, new_alias: str
    ) -> None:
        """Public API for renaming a service

        @param service_type type of service being renamed
        @param current_alias the current alias of the service
        @param new_alias the new alias for the service
        @throws: ServiceNotValid if no services of the given type are configured,
        or if no service of the given type has the current_alias
        """
        if (
            service_type == "connected_app"
            and current_alias == DEFAULT_CONNECTED_APP_NAME
        ):
            raise CumulusCIException(
                "You cannot rename the connected app service that is provided by CumulusCI."
            )

        self._validate_service_type_and_alias(service_type, current_alias)
        if new_alias in self.services[service_type]:
            raise CumulusCIUsageError(
                f"A service of type {service_type} already exists with name: {new_alias}"
            )

        self.services[service_type][new_alias] = self.services[service_type][
            current_alias
        ]
        del self.services[service_type][current_alias]

        # rename the corresponding .service file
        current_filepath = Path(
            f"{self.global_config_dir}/services/{service_type}/{current_alias}.service"
        )
        new_filepath = Path(
            f"{self.global_config_dir}/services/{service_type}/{new_alias}.service"
        )
        current_filepath.replace(new_filepath)

        # look through all DEFAULT_SERVICE.json files and
        # change current_alias to new_alias (if present)
        self._rename_alias_in_default_service_file(
            Path(self.global_config_dir, "DEFAULT_SERVICES.json"),
            service_type,
            current_alias,
            new_alias,
        )
        for project_dir in self._iter_local_project_dirs():
            self._rename_alias_in_default_service_file(
                project_dir / "DEFAULT_SERVICES.json",
                service_type,
                current_alias,
                new_alias,
            )

    def remove_service(self, service_type: str, alias: str):
        """Removes the given service from the keychain. If the service
        is the default service, and there is only one other service
        of the same type, that service is set as the new default.

        @param service_type type of the service
        @param alias the name of the service
        @raises ServiceNotConfigured if the service_type or alias are invalid
        """
        if service_type == "connected_app" and alias == DEFAULT_CONNECTED_APP_NAME:
            raise CumulusCIException(
                f"Unable to remove connected app service: {DEFAULT_CONNECTED_APP_NAME}. "
                "This connected app is provided by CumulusCI and cannot be removed."
            )

        self._validate_service_type_and_alias(service_type, alias)
        # remove the loaded service from the keychain
        del self.services[service_type][alias]

        # delete the corresponding .service file
        service_filepath = Path(
            f"{self.global_config_dir}/services/{service_type}/{alias}.service"
        )
        service_filepath.unlink()

        # remove any references from DEFAULT_SERVICES.json files
        self._remove_reference_to_alias(
            Path(self.global_config_dir, "DEFAULT_SERVICES.json"),
            service_type,
            alias,
        )
        for project_dir in self._iter_local_project_dirs():
            self._remove_reference_to_alias(
                project_dir / "DEFAULT_SERVICES.json",
                service_type,
                alias,
            )

        # if set, remove the service as the default
        if alias == self._default_services[service_type]:
            del self._default_services[service_type]
            if len(self.services[service_type].keys()) == 1:
                alias = self.list_services()[service_type][0]
                self.set_default_service(service_type, alias, project=False)

    def _remove_reference_to_alias(
        self, default_services_filepath: Path, service_type: str, alias: str
    ) -> None:
        """Given the path to a DEFAULT_SERVICES.json file, removes any references
        to the given alias if present."""
        default_services = self._read_default_services(default_services_filepath)

        if service_type in default_services and alias == default_services[service_type]:
            del default_services[service_type]

        self._write_default_services(default_services_filepath, default_services)

    def _rename_alias_in_default_service_file(
        self,
        default_service_file_path: Path,
        service_type: str,
        current_alias: str,
        new_alias: str,
    ) -> None:
        """Given the path to a DEFAULT_SERVICES.json file,
        if current_alias is present for the given service_type,
        then rename it to new_alias. Otherwise, do nothing.
        """
        default_services = self._read_default_services(default_service_file_path)

        if (
            service_type not in default_services
            or current_alias != default_services[service_type]
        ):
            return

        default_services[service_type] = new_alias
        self._write_default_services(default_service_file_path, default_services)

    def _load_services(self) -> None:
        """Load services (and migrate old ones if present)"""
        self._load_services_from_environment()

        if not (self.global_config_dir / "services").is_dir():
            self._create_default_service_files()
            self._create_services_dir_structure()
            self._migrate_services()

        self._load_service_files()

    def _set_service(
        self, service_type, alias, service_config, save=True, config_encrypted=False
    ):
        if service_type not in self.services:
            self.services[service_type] = {}
            # set the first service of a given type as the global default
            self._default_services[service_type] = alias
            if save:
                self._save_default_service(service_type, alias, project=False)

        # If the config is already encrypted coming in
        # (like when were setting services after loading from an encrypted file)
        # then we don't need to do anything.
        if self.key and config_encrypted:
            serialized_config = service_config
        else:
            serialized_config = serialize_config_to_json_or_pickle(
                service_config.config, self.logger
            )
            if self.key:
                serialized_config = encrypt_and_b64(serialized_config, self.key)

        self.services[service_type][alias] = serialized_config

        if save:
            self._save_encrypted_service(service_type, alias, serialized_config)

    def _save_encrypted_service(self, service_type, alias, encrypted):
        """Write out the encrypted service to disk."""
        service_path = Path(
            f"{self.global_config_dir}/services/{service_type}/{alias}.service"
        )
        if not service_path.parent.is_dir():
            service_path.parent.mkdir()

        fd = os.open(service_path, OS_FILE_FLAGS, SERVICE_ORG_FILE_MODE)
        with open(fd, "wb") as f:
            f.write(encrypted)

    def _get_service(self, service_type, alias):
        if service_type == "connected_app" and alias == DEFAULT_CONNECTED_APP_NAME:
            # CumulusCI's default connected app is not encrypted, just return it
            return self.config["services"]["connected_app"][DEFAULT_CONNECTED_APP_NAME]

        ConfigClass = ServiceConfig
        if "class_path" in self.project_config.config["services"][service_type]:
            class_path = self.project_config.config["services"][service_type][
                "class_path"
            ]
            try:
                ConfigClass = import_class(class_path)
            except (AttributeError, ModuleNotFoundError):
                raise CumulusCIException(
                    f"Unrecognized class_path for service: {class_path}"
                )

        try:
            config = self.services[service_type][alias]
        except KeyError:
            raise ServiceNotConfigured(
                f"No service of type {service_type} exists with the name: {alias}"
            )

        if self.key:
            org = self._decrypt_config(
                ConfigClass,
                config,
                extra=[alias, self],
                context=f"service config ({service_type}:{alias})",
            )
        else:
            config = load_config_from_json_or_pickle(config)
            org = self._construct_config(ConfigClass, [config, alias, self])

        return org

    def _load_services_from_environment(self):
        """Load any services specified by environment variables"""
        for env_var_name, value in os.environ.items():
            if env_var_name.startswith(self.env_service_var_prefix):
                self._load_service_from_environment(env_var_name, value)

    def _load_service_from_environment(self, env_var_name, value):
        """Given a valid name/value pair, load the
        service from the environment on to the keychain"""
        service_config = ServiceConfig(json.loads(value))
        service_type, service_name = self._get_env_service_type_and_name(env_var_name)
        self.set_service(service_type, service_name, service_config, save=False)

    def _get_env_service_type_and_name(self, env_service_name):
        return (
            self._get_env_service_type(env_service_name),
            self._get_env_service_name(env_service_name),
        )

    def _get_env_service_type(self, env_service_name):
        """Parse the service type given the env var name"""
        post_prefix = env_service_name[len(self.env_service_var_prefix) :].lower()
        return post_prefix.split("__")[0]

    def _get_env_service_name(self, env_service_name):
        """
        Parse the service name given the env var name.
        Services from the environment can be listed with or without a name:
        * CUMULUSCI_SERVICE_service_type -> this gets a default name of "env"
        * CUMULUSCI_SERVICE_service_type__name -> this gets the name "env-name"
        """
        parts = env_service_name.split("__")
        return f"env-{parts[-1]}" if len(parts) > 1 else "env"

    def _load_service_files(self) -> None:
        """
        Load configured services onto the keychain.
        This method recursively goes through all subdirectories
        in ~/.cumulusci/services looking for .service files to load.
        """
        services_dir = Path(f"{self.global_config_dir}/services")
        for item in services_dir.glob("**/*"):
            if item.suffix == ".service":
                with open(item) as f:
                    config = f.read()
                name = item.name.replace(".service", "")
                service_type = item.parent.name

                self.set_service(
                    service_type, name, config, save=False, config_encrypted=True
                )

    def _load_default_services(self) -> None:
        """Init self._default_services on the keychain so that
        calls to get_service() that do not pass an alias can
        return the default service for the given type"""

        # set CumulusCI's default connected app as the default first
        # so it will be overwritten if the user is using a different connected app
        self._default_services["connected_app"] = DEFAULT_CONNECTED_APP_NAME

        global_default_services = Path(
            f"{self.global_config_dir}/{DEFAULT_SERVICES_FILENAME}"
        )
        self._set_default_services_from_dir(global_default_services)

        project_default_services = Path(
            f"{self.project_local_dir}/{DEFAULT_SERVICES_FILENAME}"
        )
        # project defaults will overwrite global defaults
        self._set_default_services_from_dir(project_default_services)

    def _set_default_services_from_dir(self, default_services_file: Path) -> None:
        """Sets the keychain._default_services dictionary to the default
        values in the given file.

        @param default_services_file path to a DEFAULT_SERVICES.json file
        """
        default_services = self._read_default_services(default_services_file)
        for s_type, alias in default_services.items():
            self._default_services[s_type] = alias

    def _save_default_service(
        self, service_type: str, alias: str, project: bool = False
    ) -> None:
        """Write out the contents of self._default_services to the
        DEFAULT_SERVICES.json file based on the provided scope"""
        dir_path = (
            Path(self.project_local_dir) if project else Path(self.global_config_dir)
        )
        default_services_file = dir_path / DEFAULT_SERVICES_FILENAME

        default_services = self._read_default_services(default_services_file)
        default_services[service_type] = alias
        self._write_default_services(default_services_file, default_services)

    def _create_default_service_files(self) -> None:
        """
        Generate the DEFAULT_SERVICES.json files at global and project scopes.

        @param local_proj_path: should be the local_project_path for the project
        """
        global_default_service_file = Path(
            f"{self.global_config_dir}/{DEFAULT_SERVICES_FILENAME}"
        )
        if global_default_service_file.is_file():
            return

        self._write_default_services_for_dir(self.global_config_dir)
        for local_proj_dir in self._iter_local_project_dirs():
            self._write_default_services_for_dir(local_proj_dir)

    def _write_default_services_for_dir(self, dir_path: str) -> None:
        """Look through the given dir and set all .service files
        present as the defaults for their given types, and write these
        out to a DEFAULT_SERVICES.json file in the directory. This occurs
        once before .service files are migrated to the appropriate
        services/ sub-directory, so we set the default to the alias
        that will be assigned during migration.

        @param dir_path: the directory to look through and write
        the DEFAULT_SERVICES.json file in.
        """
        dir_path = Path(dir_path)
        default_services = {}
        for item in dir_path.iterdir():
            if item.suffix == ".service":
                service_type = item.name.replace(".service", "")
                alias = (
                    "global"
                    if item.parent.name == ".cumulusci"
                    else Path(self.project_local_dir).name
                )
                default_services[service_type] = f"{alias}"

        self._write_default_services(
            dir_path / DEFAULT_SERVICES_FILENAME, default_services
        )

    def _create_services_dir_structure(self) -> None:
        """
        Ensure the 'services' directory structure exists.
        The services dir has the following structure and lives
        in the global_config_dir:

        services
        |-- github
        |   |-- alias1.service
        |   |-- alias2.service
        |   |-- ...
        |-- devhub
        |   |-- alias1.service
        |   |-- alias2.service
        |   |-- ...
        .

        This also has the advantage that when a new service type
        is added to cumulusci.yml a new directory for that service type
        will be created.
        """
        services_dir_path = Path(f"{self.global_config_dir}/services")
        services_dir_path.mkdir(exist_ok=True)

        configured_service_types = self.project_config.config["services"].keys()
        for service_type in configured_service_types:
            service_type_dir_path = Path(services_dir_path / service_type)
            if not Path.is_dir(service_type_dir_path):
                Path.mkdir(service_type_dir_path)

    def _migrate_services(self):
        """Migrate .service files from the global_config_dir and
        any project local directories."""
        self._migrate_services_from_dir(self.global_config_dir)
        for local_proj_dir in self._iter_local_project_dirs():
            self._migrate_services_from_dir(local_proj_dir)

    def _migrate_services_from_dir(self, dir_path: str) -> None:
        """Migrate all .service files from the given directory to
        the appropriate service sub-directory and apply the default
        alias. This is intended to be run against either the
        global_config_dir, or a local project directory.

        Default aliases are in the form `service_type__scope`.
        Scope is either the name of the local project directory
        or 'global'; depending on where the .service file is located."""
        dir_path = Path(dir_path)
        for item in dir_path.iterdir():
            if item.suffix == ".service":
                new_service_filepath = self._get_new_service_filepath(item)
                if not new_service_filepath:
                    continue
                if new_service_filepath.is_file():
                    self.logger.warning(
                        f"Skipping migration of {item.name} as a default alias already exists for this service type. "
                    )
                    continue

                item.replace(new_service_filepath)

    def _get_new_service_filepath(self, item: Path) -> Path:
        """Given an old .service filepath, determine the path
        and filename of the new .service file.

        @returns: the Path to the newfile, or None if the service
        is of an unrecognized type.
        """
        service_type = item.name.replace(".service", "")
        configured_service_types = self.project_config.config["services"].keys()
        if service_type not in configured_service_types:
            self.logger.info(f"Skipping migration of unrecognized service: {item.name}")
            return None

        alias = (
            "global"
            if item.parent.name == ".cumulusci"
            else Path(self.project_local_dir).name
        )
        new_filename = f"{alias}.service"
        services_sub_dir = Path(f"{self.global_config_dir}/services/{service_type}")
        return services_sub_dir / new_filename

    def _read_default_services(self, file_path: Path) -> T.Dict[str, str]:
        """Reads the default services file at the given path

        @param file_path path to DEFAULT_SERVICES.json
        @returns dict of default services
        @raises CumulusCIException if the file does not exist
        """
        if not file_path.is_file() or file_path.name != DEFAULT_SERVICES_FILENAME:
            return {}
        else:
            return json.loads(file_path.read_text(encoding="utf-8"))

    def _write_default_services(
        self, file_path: Path, default_services: T.Dict[str, str]
    ) -> None:
        """Writes default services out to the given file

        @param file_path path to DEFAULT_SERVICES.json
        @param dictionary mapping service types to the alias of the default service for that type
        @raises CumulusCIException if the file does not exist
        """
        if file_path.name != DEFAULT_SERVICES_FILENAME:
            raise CumulusCIException(
                f"No {DEFAULT_SERVICES_FILENAME} file found at: {file_path}"
            )

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(default_services))

    def _iter_local_project_dirs(self):
        """Iterate over all local project dirs in ~/.cumulusci"""
        for item in Path(self.global_config_dir).iterdir():
            if item.is_dir() and item.name not in ["logs", "services"]:
                yield item

    def _raise_service_not_configured(self, name):
        raise ServiceNotConfigured(
            f"'{name}' service configuration could not be found. "
            f"Maybe you need to run: cci service connect {name}"
        )


class GlobalOrg(T.NamedTuple):
    data: bytes
    global_org: bool = True
    filename: str = None


class LocalOrg(T.NamedTuple):
    data: bytes
    global_org: bool = False
    filename: str = None

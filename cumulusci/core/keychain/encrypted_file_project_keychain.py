import os
import json
import typing as T

from pathlib import Path

from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import OrgNotFound, ServiceNotConfigured, ServiceNotValid
from cumulusci.core.keychain import BaseEncryptedProjectKeychain

DEFAULT_SERVICES_FILENAME = "DEFAULT_SERVICES.json"


class EncryptedFileProjectKeychain(BaseEncryptedProjectKeychain):
    """ An encrypted project keychain that stores in the project's local directory """

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

    def _load_org_files(self, dirname: str, constructor=None):
        """Loads .org files in a given directory onto the keychain"""
        if not dirname:
            return
        dir_path = Path(dirname)
        for item in sorted(dir_path.iterdir()):
            if item.suffix == ".org":
                with open(item, "r") as f:
                    config = f.read()
                name = item.name.replace(".org", "")
                if "orgs" not in self.config:
                    self.config["orgs"] = {}
                self.config["orgs"][name] = (
                    constructor(config) if constructor else config
                )

    def _load_service_files(self, constructor=None) -> None:
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
                if "services" not in self.config:
                    self.config["services"] = {}
                name = item.name.replace(".service", "")
                service_type = item.parent.name
                if service_type not in self.config["services"]:
                    self.config["services"][service_type] = {}
                self.config["services"][service_type][name] = (
                    constructor(config) if constructor else config
                )

    def _init_default_services(self) -> None:
        """Init self._default_services on the keychain so that
        calls to get_service() that do not pass an alias can
        return the default service for the given type"""
        global_default_services = Path(
            f"{self.global_config_dir}/{DEFAULT_SERVICES_FILENAME}"
        )
        project_default_services = Path(
            f"{self.project_local_dir}/{DEFAULT_SERVICES_FILENAME}"
        )

        if global_default_services.is_file():
            with open(global_default_services, "r") as f:
                default_services = json.loads(f.read())

            for s_type, alias in default_services.items():
                self._default_services[s_type] = alias

        # project defaults will overwrite global defaults
        if project_default_services.is_file():
            with open(global_default_services, "r") as f:
                default_services = json.loads(f.read())

            for s_type, alias in default_services.items():
                self._default_services[s_type] = alias

    def set_default_service(
        self, service_type: str, alias: str, project: bool = False
    ) -> None:
        """Public API for setting a default service e.g. `cci service default`"""
        if service_type not in self.project_config.services:
            raise ServiceNotValid(f"No such service type: {service_type}")
        elif alias not in self.services[service_type]:
            raise ServiceNotConfigured(
                f"No service of type {service_type} configured with name: {alias}"
            )

        self._default_services[service_type] = alias
        self._save_default_services(project)

    def _save_default_services(self, project: bool = False) -> None:
        """Write out the contents of self.default_services to the
        DEFAULT_SERVICES.json file based on the provided scope"""
        dir_path = (
            Path(self.project_local_dir) if project else Path(self.global_config_dir)
        )
        with open(dir_path / DEFAULT_SERVICES_FILENAME, "w") as f:
            f.write(json.dumps(self.default_services))

    def _load_app_file(self, dirname: str, filename: str, key: str) -> None:
        """This is only used for loading the legacy connected_app configurations"""
        if dirname is None:
            return
        full_path = Path(f"{dirname}/{filename}")
        if not os.path.exists(full_path):
            return
        with open(os.path.join(dirname, filename), "r") as f_item:
            config = f_item.read()
        self.config[key] = config

    def _load_app(self) -> None:
        self._load_app_file(self.global_config_dir, "connected.app", "app")
        self._load_app_file(self.project_local_dir, "connected.app", "app")

    def _load_orgs(self) -> None:
        self._load_org_files(self.global_config_dir, GlobalOrg)
        self._load_org_files(self.project_local_dir, LocalOrg)

    def _load_services(self) -> None:
        """Load services (and migrate old ones if present)"""
        # The following steps occur in a _very_ particular order
        self._create_default_service_files()
        self._create_services_dir_structure()
        self._migrate_services()
        self._load_service_files()

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
        if dir_path is None:
            return  # pragma: no cover

        dir_path = Path(dir_path)
        default_services = {}
        for item in dir_path.iterdir():
            if item.suffix == ".service":
                service_type = item.name.replace(".service", "")
                scope = "global" if item.parent.name == ".cumulusci" else "project"
                default_services[service_type] = f"{service_type}__{scope}"

        with open(dir_path / DEFAULT_SERVICES_FILENAME, "w") as f:
            f.write(json.dumps(default_services))

    def _iter_local_project_dirs(self):
        """Iterate over all local project dirs in ~/.cumulusci"""
        for item in Path(self.global_config_dir).iterdir():
            if item.is_dir() and item.name not in ["logs", "services"]:
                yield item

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
        if not Path.is_dir(services_dir_path):
            Path.mkdir(services_dir_path)

        configured_service_types = self.project_config.config["services"].keys()
        for service_type in configured_service_types:
            service_type_dir_path = Path(services_dir_path / service_type)
            if not Path.is_dir(service_type_dir_path):
                Path.mkdir(service_type_dir_path)

    def _migrate_services(self):
        """
        Migrate .service files from the global_config_dir and
        any project local directories.
        """
        self._migrate_services_from_dir(self.global_config_dir)
        for local_proj_dir in self._iter_local_project_dirs():
            self._migrate_services_from_dir(local_proj_dir)

    def _migrate_services_from_dir(self, dir_path: str) -> None:
        """
        Migrate all .service files from the given directory to
        the appropriate service sub-directory and apply the default
        alias. This is intended to be run against either the
        global_config_dir, or a local project directory.

        Default aliases are in the form `service_type__scope`.
        Scope is either 'project' or 'global' depending
        on where the .service file is located.
        """
        if not dir_path:
            return  # pragma: no cover

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

        scope = "global" if item.parent.name == ".cumulusci" else "project"
        new_filename = f"{service_type}__{scope}.service"
        services_sub_dir = Path(f"{self.global_config_dir}/services/{service_type}")
        return services_sub_dir / new_filename

    def _remove_org(self, name, global_org):
        if global_org:
            full_path = os.path.join(self.global_config_dir, f"{name}.org")
        else:
            full_path = os.path.join(self.project_local_dir, f"{name}.org")
        if not os.path.exists(full_path):
            kwargs = {"name": name}
            if not global_org:
                raise OrgNotFound(
                    "Could not find org named {name} to delete.  Deleting in project org mode.  Is {name} a global org?".format(
                        **kwargs
                    )
                )
            raise OrgNotFound(
                "Could not find org named {name} to delete.  Deleting in global org mode.  Is {name} a project org instead of a global org?".format(
                    **kwargs
                )
            )

        os.remove(full_path)
        del self.orgs[name]

    def _set_encrypted_org(self, name, encrypted, global_org):
        if global_org:
            filename = os.path.join(self.global_config_dir, f"{name}.org")
        elif self.project_local_dir is None:
            return
        else:
            filename = os.path.join(self.project_local_dir, f"{name}.org")
        with open(filename, "wb") as f_org:
            f_org.write(encrypted)

    def _set_encrypted_service(self, service_type, alias, encrypted, project):
        service_path = Path(
            f"{self.global_config_dir}/services/{service_type}/{alias}.service"
        )
        with open(service_path, "wb") as f:
            f.write(encrypted)

    def _raise_org_not_found(self, name):
        raise OrgNotFound(
            f"Org information could not be found. Expected to find encrypted file at {self.project_local_dir}/{name}.org"
        )

    def _raise_service_not_configured(self, name):
        raise ServiceNotConfigured(  # pragma: no cover
            f"'{name}' service configuration could not be found. "
            f"Maybe you need to run: cci service connect {name}"
        )

    def _get_org(self, name):
        org = self._decrypt_config(
            OrgConfig,
            self.orgs[name].encrypted_data,
            extra=[name, self],
            context=f"org config ({name})",
        )
        if self.orgs[name].global_org:
            org.global_org = True
        return org

    @property
    def _default_org_path(self):
        if self.project_local_dir:
            return Path(self.project_local_dir) / "DEFAULT_ORG.txt"

    def get_default_org(self):
        """ Retrieve the name and configuration of the default org """
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
        """ Set the default org for tasks and flows by name """
        super().set_default_org(name)
        self._default_org_path.write_text(name)

    def unset_default_org(self):
        """Unset the default orgs for tasks and flows """
        super().unset_default_org()
        if self._default_org_path:
            try:
                self._default_org_path.unlink()
            except FileNotFoundError:
                pass


class GlobalOrg(T.NamedTuple):
    encrypted_data: bytes
    global_org: bool = True


class LocalOrg(T.NamedTuple):
    encrypted_data: bytes
    global_org: bool = False

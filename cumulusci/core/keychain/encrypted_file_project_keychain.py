import json
import typing as T

from pathlib import Path

from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import (
    CumulusCIException,
    OrgNotFound,
    ServiceNotConfigured,
)
from cumulusci.core.keychain import BaseEncryptedProjectKeychain

DEFAULT_SERVICES_FILENAME = "DEFAULT_SERVICES.json"


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


class EncryptedFileProjectKeychain(BaseEncryptedProjectKeychain):
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
    #               Orgs                  #
    #######################################

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

    @property
    def _default_org_path(self):
        if self.project_local_dir:
            return Path(self.project_local_dir) / "DEFAULT_ORG.txt"

    def _load_orgs(self) -> None:
        self._load_org_files(self.global_config_dir, GlobalOrg)
        self._load_org_files(self.project_local_dir, LocalOrg)

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

    def _set_encrypted_org(self, name, encrypted, global_org):
        if global_org:
            filename = Path(f"{self.global_config_dir}/{name}.org")
        elif self.project_local_dir is None:
            return
        else:
            filename = Path(f"{self.project_local_dir}/{name}.org")
        with open(filename, "wb") as f_org:
            f_org.write(encrypted)

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

    def _raise_org_not_found(self, name):
        raise OrgNotFound(
            f"Org information could not be found. Expected to find encrypted file at {self.project_local_dir}/{name}.org"
        )

    #######################################
    #              Services               #
    #######################################

    def set_default_service(
        self, service_type: str, alias: str, project: bool = False
    ) -> None:
        """Public API for setting a default service e.g. `cci service default`"""
        if service_type not in self.project_config.services:
            raise ServiceNotConfigured(f"No such service type: {service_type}")
        elif alias not in self.services[service_type]:
            raise ServiceNotConfigured(
                f"No service of type {service_type} configured with name: {alias}"
            )

        self._default_services[service_type] = alias
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

        if service_type not in self.services:
            raise ServiceNotConfigured(
                f"No services of type {service_type} are currently configured"
            )
        elif current_alias not in self.services[service_type]:
            raise ServiceNotConfigured(
                f"No service of type {service_type} configured with the name: {current_alias}"
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
        if not (self.global_config_dir / "services").is_dir():
            self._create_default_service_files()
            self._create_services_dir_structure()
            self._migrate_services()
        self._load_service_files()

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

    def _set_encrypted_service(self, service_type, alias, encrypted):
        service_path = Path(
            f"{self.global_config_dir}/services/{service_type}/{alias}.service"
        )
        with open(service_path, "wb") as f:
            f.write(encrypted)

    def _load_default_services(self) -> None:
        """Init self._default_services on the keychain so that
        calls to get_service() that do not pass an alias can
        return the default service for the given type"""
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
        if default_services_file.is_file():
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
                scope = (
                    "global" if item.parent.name == ".cumulusci" else item.parent.name
                )
                default_services[service_type] = f"{service_type}__{scope}"

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

        scope = "global" if item.parent.name == ".cumulusci" else "project"
        new_filename = f"{service_type}__{scope}.service"
        services_sub_dir = Path(f"{self.global_config_dir}/services/{service_type}")
        return services_sub_dir / new_filename

    def _read_default_services(self, file_path: Path) -> T.Dict[str, str]:
        """Reads the default services file at the given path

        @param file_path path to DEFAULT_SERVICES.json
        @returns dict of default services
        @raises CumulusCIException if the file does not exist
        """
        if not file_path.is_file() or file_path.name != DEFAULT_SERVICES_FILENAME:
            raise CumulusCIException(
                f"No {DEFAULT_SERVICES_FILENAME} file found at: {file_path}"
            )

        with open(file_path, "r") as f:
            return json.loads(f.read())

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

        with open(file_path, "w") as f:
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
    encrypted_data: bytes
    global_org: bool = True


class LocalOrg(T.NamedTuple):
    encrypted_data: bytes
    global_org: bool = False

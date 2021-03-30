import os
import json
import typing as T

from pathlib import Path

from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import OrgNotFound, ServiceNotConfigured
from cumulusci.core.keychain import BaseEncryptedProjectKeychain

# TODO: figure out circular import
DEFAULT_SERVICE_ALIAS = "default"


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

    def _load_service_files(self, dirname: str, constructor=None) -> None:
        """
        Loads .service files onto the keychain.
        This method recursively goes through all subdirectories
        looking for .service files.
        """
        if not dirname:
            return
        dir_path = Path(dirname)
        for item in dir_path.glob("**/*"):
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

    def _load_file(self, dirname: str, filename: str, key: str) -> None:
        if dirname is None:
            return
        full_path = os.path.join(dirname, filename)
        if not os.path.exists(full_path):
            return
        with open(os.path.join(dirname, filename), "r") as f_item:
            config = f_item.read()
        self.config[key] = config

    def _load_app(self) -> None:
        self._load_file(self.global_config_dir, "connected.app", "app")
        self._load_file(self.project_local_dir, "connected.app", "app")

    def _load_orgs(self) -> None:
        self._load_org_files(self.global_config_dir, GlobalOrg)
        self._load_org_files(self.project_local_dir, LocalOrg)

    def _load_services(self) -> None:
        self._create_default_services_file(self.project_local_dir)

        self._create_services_dir_structure(self.global_config_dir)
        self._convert_unaliased_services(self.global_config_dir)

        services_dir = Path(f"{self.global_config_dir}/services")
        self._load_service_files(services_dir)

    def _create_default_services_file(self, dir_path: str) -> None:
        """
        Creates the DEFAULT_SERVICES.json file if it does not yet exist.
        This _should_ occur once, right before initial migration of service
        files has been performed. This allows us to set any services configured
        at the project level as the default service for the given service type.
        """
        if not dir_path:
            return
        dir_path = Path(dir_path)
        default_services_file = dir_path / "DEFAULT_SERVICES.json"
        if default_services_file.is_file():
            return
        default_services_file.touch()

        default_services = {s_type: {} for s_type in self.services}
        self._set_default_services_in_dir(dir_path.parent, default_services, "global")
        # set defaults in project dir second, so they override any global defaults
        self._set_default_services_in_dir(dir_path, default_services, "project")

        with open(default_services_file, "w") as f:
            f.write(json.dumps(default_services))

    def _set_default_services_in_dir(
        self, dir_path: Path, default_services: T.Dict, scope: str
    ) -> None:
        for item in dir_path.iterdir():
            if item.suffix == ".service":
                # this .service file has not yet been migrated
                # so it's name is the type of service (not its alias)
                service_type = item.name.replace(".service", "")
                # TODO: get default name from constant
                default_services[service_type] = f"{service_type}__{scope}"

    def _create_services_dir_structure(self, dir_path: str) -> None:
        """
        Given a directory, ensure that the 'services' directory sturcutre exists.
        The services dir has the following structure:

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
        .
        .

        This also has the advantage that when we add a new service
        type to cumulusci.yml a new directory for that service type
        will be created the first time services are loaded.
        """
        services_dir_path = Path(f"{dir_path}/services")
        # ensure a root service/ dir exists
        if not Path.is_dir(services_dir_path):
            Path.mkdir(services_dir_path)

        configured_service_types = self.project_config.config["services"].keys()
        for service_type in configured_service_types:
            service_type_dir_path = Path(services_dir_path / service_type)
            # ensure a dir for each service type exists
            if not Path.is_dir(service_type_dir_path):
                Path.mkdir(service_type_dir_path)

    def _convert_unaliased_services(self, dir_path: str):
        """Look in the given dir for any files with the .services extension and
        move them to the proper directory with the defualt alias."""
        configured_service_types = self.project_config.config["services"].keys()

        for item in Path(dir_path).iterdir():
            if item.suffix == ".service":
                service_type = item.name.replace(".service", "")
                if service_type not in configured_service_types:
                    continue  # we don't care about unrecognized services

                service_type_path = Path(f"{dir_path}/services/{service_type}")
                default_service_filename = (
                    f"{service_type}_{DEFAULT_SERVICE_ALIAS}.service"
                )
                default_service_path = Path(
                    service_type_path / default_service_filename
                )

                if Path.is_file(default_service_path):
                    self.logger.warning(
                        f"Found {service_type}.serive in ~/.cumulusci and default alias already exists."
                    )
                else:
                    original_service_path = Path(f"{dir_path}/{service_type}.service")
                    original_service_path.replace(default_service_path)

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

    def _set_encrypted_service(self, service_type, name, encrypted, project):
        service_path = Path(
            f"{self.global_config_dir}/services/{service_type}/{name}.service"
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

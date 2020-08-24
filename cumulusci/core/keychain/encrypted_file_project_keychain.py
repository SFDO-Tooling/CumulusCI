import os
from typing import NamedTuple
from pathlib import Path

from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.keychain import BaseEncryptedProjectKeychain
from cumulusci.core.config import OrgConfig


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

    def _load_files(self, dirname, extension, key, constructor=None):
        if dirname is None:
            return
        for item in sorted(os.listdir(dirname)):
            if item.endswith(extension):
                with open(os.path.join(dirname, item), "r") as f_item:
                    config = f_item.read()
                name = item.replace(extension, "")
                if key not in self.config:
                    self.config[key] = {}
                self.config[key][name] = constructor(config) if constructor else config

    def _load_file(self, dirname, filename, key):
        if dirname is None:
            return
        full_path = os.path.join(dirname, filename)
        if not os.path.exists(full_path):
            return
        with open(os.path.join(dirname, filename), "r") as f_item:
            config = f_item.read()
        self.config[key] = config

    def _load_app(self):
        self._load_file(self.global_config_dir, "connected.app", "app")
        self._load_file(self.project_local_dir, "connected.app", "app")

    def _load_orgs(self):
        self._load_files(self.global_config_dir, ".org", "orgs", GlobalOrg)

        self._load_files(self.project_local_dir, ".org", "orgs", LocalOrg)

    def _load_services(self):
        self._load_files(self.global_config_dir, ".service", "services")
        self._load_files(self.project_local_dir, ".service", "services")

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

    def _set_encrypted_service(self, name, encrypted, project):
        if project:
            filename = os.path.join(self.project_local_dir, f"{name}.service")
        else:
            filename = os.path.join(self.global_config_dir, f"{name}.service")
        with open(filename, "wb") as f_service:
            f_service.write(encrypted)

    def _raise_org_not_found(self, name):
        raise OrgNotFound(
            f"Org information could not be found. Expected to find encrypted file at {self.project_local_dir}/{name}.org"
        )

    def _raise_service_not_configured(self, name):
        raise ServiceNotConfigured(
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
        return Path(self.project_local_dir) / "DEFAULT_ORG.txt"

    def get_default_org(self):
        """ Retrieve the name and configuration of the default org """
        # first look for a file with the default org in it
        default_org_path = self._default_org_path
        if default_org_path.exists():
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
        try:
            self._default_org_path.unlink()
        except FileNotFoundError:
            pass


class GlobalOrg(NamedTuple):
    encrypted_data: bytes
    global_org: bool = True


class LocalOrg(NamedTuple):
    encrypted_data: bytes
    global_org: bool = False

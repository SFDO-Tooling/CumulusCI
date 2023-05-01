import functools
import logging
from typing import Optional, cast

from simple_salesforce.api import SFType
from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.config import OrgConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.dependencies.utils import TaskContext
from cumulusci.core.enums import StrEnum
from cumulusci.core.exceptions import PackageInstallError, TaskOptionsError
from cumulusci.core.utils import process_bool_arg
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.utils.waiting import poll, retry
from cumulusci.utils.yaml.model_parser import CCIModel

logger = logging.getLogger(__name__)


class SecurityType(StrEnum):
    """Enum used to specify the component permissioning mode for a package install.

    The values specified by the Tooling API are confusing, and PUSH is not documented.
    We rename here for a little bit of clarity."""

    FULL = "FULL"  # All profiles
    CUSTOM = "CUSTOM"  # Custom profiles
    ADMIN = "NONE"  # System Administrator only
    PUSH = "PUSH"  # No profiles


class NameConflictResolution(StrEnum):
    """Enum used to specify how name conflicts will be resolved when installing an Unlocked Package."""

    BLOCK = "Block"
    RENAME = "RenameMetadata"


# Unlocked Packages only. Default appears to be all but is not documented.
class ApexCompileType(StrEnum):
    ALL = "all"
    PACKAGE = "package"


# Unlocked Packages only. Default is mixed.
class UpgradeType(StrEnum):
    DELETE_ONLY = "delete-only"
    DEPRECATE_ONLY = "deprecate-only"
    MIXED = "mixed"


class PackageInstallOptions(CCIModel):
    """Options governing installation behavior for a managed or unlocked package."""

    activate_remote_site_settings: bool = True
    name_conflict_resolution: NameConflictResolution = NameConflictResolution.BLOCK
    password: Optional[str] = None
    security_type: SecurityType = SecurityType.FULL
    apex_compile_type: Optional[ApexCompileType] = None
    upgrade_type: Optional[UpgradeType] = None

    @staticmethod
    def from_task_options(task_options: dict) -> "PackageInstallOptions":
        options = PackageInstallOptions()  # all parameters are defaulted

        try:
            if "security_type" in task_options:
                options.security_type = SecurityType(task_options["security_type"])
            if "activate_remote_site_settings" in task_options:
                options.activate_remote_site_settings = process_bool_arg(
                    task_options["activate_remote_site_settings"]
                )
            if "name_conflict_resolution" in task_options:
                options.name_conflict_resolution = NameConflictResolution(
                    task_options["name_conflict_resolution"]
                )
            if "password" in task_options:
                options.password = task_options["password"]
            if "apex_compile_type" in task_options:
                options.apex_compile_type = ApexCompileType(
                    task_options["apex_compile_type"]
                )
            if "upgrade_type" in task_options:
                options.upgrade_type = UpgradeType(task_options["upgrade_type"])
        except ValueError as e:
            raise TaskOptionsError(f"Invalid task options: {e}")

        return options


PackageInstallOptions.update_forward_refs()

PACKAGE_INSTALL_TASK_OPTIONS = {
    "security_type": {
        "description": "Which Profiles to install packages for (FULL = all profiles, NONE = admins only, PUSH = no profiles, CUSTOM = custom profiles). Defaults to FULL."
    },
    "name_conflict_resolution": {
        "description": "Specify how to resolve name conflicts when installing an Unlocked Package. Available values are Block and RenameMetadata. Defaults to Block."
    },
    "activate_remote_site_settings": {
        "description": "Activate Remote Site Settings when installing a package. Defaults to True."
    },
    "password": {"description": "The installation key for the managed package."},
    "apex_compile_type": {
        "description": "For Unlocked Packages only, whether to compile Apex in the package only (`package`) or in the whole org (`all`). `all` is the default behavior."
    },
    "upgrade_type": {
        "description": "For Unlocked Package upgrades only, whether to deprecate removed components (`deprecate-only`), delete them (`delete-only`), or delete and deprecate based on safety (`mixed`). `mixed` is the default behavior."
    },
}

DEFAULT_PACKAGE_RETRY_OPTIONS = {
    "retries": 20,
    "retry_interval": 5,
    "retry_interval_add": 30,
}

RETRY_PACKAGE_ERRORS = [
    "This package is not yet available",
    "InstalledPackage version number",
    "The requested package doesn't yet exist or has been deleted",
    "unable to obtain exclusive access to this record",
    "invalid cross reference id",
]


def _wait_for_package_install(tooling, request):
    res = tooling.query(
        f"SELECT Errors, Status FROM PackageInstallRequest WHERE Id='{request['id']}'"
    )
    request = res["records"][0]
    if request["Status"] == "IN_PROGRESS":
        logger.info("In Progress")
        return False

    if request["Status"] == "SUCCESS":
        logger.info("Success")
        return True

    if request["Status"] == "ERROR":
        logger.error("Error installing package")
        raise PackageInstallError(
            "\n".join(error["message"] for error in request["Errors"]["errors"])
        )


def _install_package_by_version_id(
    project_config: BaseProjectConfig,
    org_config: OrgConfig,
    version_id: str,
    options: PackageInstallOptions,
):
    """Install a 1gp or 2gp package using PackageInstallRequest"""
    tooling = get_simple_salesforce_connection(
        project_config, org_config, base_url="tooling"
    )
    PackageInstallRequest = cast(SFType, tooling.PackageInstallRequest)
    PackageInstallRequest.base_url = PackageInstallRequest.base_url.replace(
        "/sobjects/", "/tooling/sobjects/"
    )
    request = PackageInstallRequest.create(
        {
            "EnableRss": options.activate_remote_site_settings,
            "NameConflictResolution": options.name_conflict_resolution,
            "Password": options.password,
            "SecurityType": options.security_type,
            "SubscriberPackageVersionKey": version_id,
            "UpgradeType": options.upgrade_type,
            "ApexCompileType": options.apex_compile_type,
        }
    )
    poll(functools.partial(_wait_for_package_install, tooling, request))


def _should_retry_package_install(e: Exception) -> bool:
    return isinstance(e, (SalesforceMalformedRequest, MetadataApiError)) and any(
        err in str(e) for err in RETRY_PACKAGE_ERRORS
    )


def _install_package_by_namespace_version(
    project_config: BaseProjectConfig,
    org_config: OrgConfig,
    namespace: str,
    version: str,
    install_options: PackageInstallOptions,
    retry_options=None,
):
    task = TaskContext(
        org_config=org_config, project_config=project_config, logger=logger
    )

    retry_options = {
        **(retry_options or {}),
        "should_retry": _should_retry_package_install,
    }

    def deploy():
        package_zip = InstallPackageZipBuilder(
            namespace=namespace,
            version=version,
            activateRSS=install_options.activate_remote_site_settings,
            password=install_options.password,
            securityType=install_options.security_type,
        )
        ApiDeploy(task, package_zip(), purge_on_delete=False)()

    retry(
        deploy,
        **retry_options,
    )


def install_package_by_version_id(
    project_config: BaseProjectConfig,
    org_config: OrgConfig,
    version_id: str,
    install_options: PackageInstallOptions,
    retry_options=None,
):
    """Install a 1gp or 2gp package using PackageInstallRequest, with retries"""
    retry_options = {
        **(retry_options or {}),
        "should_retry": _should_retry_package_install,
    }
    retry(
        functools.partial(
            _install_package_by_version_id,
            project_config,
            org_config,
            version_id,
            install_options,
        ),
        **retry_options,
    )


def install_package_by_namespace_version(
    project_config: BaseProjectConfig,
    org_config: OrgConfig,
    namespace: str,
    version: str,
    install_options: PackageInstallOptions,
    retry_options=None,
):
    """Install a 1gp package by deploying InstalledPackage metadata, with retries"""
    retry_options = {
        **(retry_options or {}),
        "should_retry": _should_retry_package_install,
    }
    retry(
        functools.partial(
            _install_package_by_namespace_version,
            project_config,
            org_config,
            namespace,
            version,
            install_options,
        ),
        **retry_options,
    )

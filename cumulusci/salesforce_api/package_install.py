from cumulusci.utils.yaml.model_parser import CCIModel
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.salesforce_api.package_zip import InstallPackageZipBuilder
from cumulusci.salesforce_api.metadata import ApiDeploy
from cumulusci.core.config import OrgConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from typing import Optional, cast
import functools
import logging
from enum import Enum
from simple_salesforce.api import SFType
from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.exceptions import PackageInstallError
from cumulusci.core.dependencies.utils import TaskContext

from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.utils.waiting import poll, retry

logger = logging.getLogger(__name__)


class SecurityType(str, Enum):
    """Enum used to specify the component permissioning mode for a package install.

    The values specified by the Tooling API are confusing, and PUSH is not documented.
    We rename here for a little bit of clarity."""

    FULL = "FULL"  # All profiles
    CUSTOM = "CUSTOM"  # Custom profiles
    ADMIN = "NONE"  # System Administrator only
    PUSH = "PUSH"  # No profiles


class NameConflictResolution(str, Enum):
    """Enum used to specify how name conflicts will be resolved when installing
    an Unlocked Package."""

    BLOCK = "Block"
    RENAME = "RenameMetadata"


class PackageInstallOptions(CCIModel):
    """Options governing installation behavior for a managed or unlocked package."""

    activate_remote_site_settings: Optional[bool] = True
    name_conflict_resolution: NameConflictResolution = NameConflictResolution.BLOCK
    password: Optional[str]
    security_type: SecurityType = SecurityType.FULL


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

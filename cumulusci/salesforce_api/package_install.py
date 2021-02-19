from typing import cast
import functools
import logging

from simple_salesforce.api import SFType
from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.core.exceptions import PackageInstallError
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.utils.waiting import poll, retry

logger = logging.getLogger(__name__)


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


def _install_package_version(project_config, org_config, options):
    tooling = get_simple_salesforce_connection(
        project_config, org_config, base_url="tooling"
    )
    PackageInstallRequest = cast(SFType, tooling.PackageInstallRequest)
    PackageInstallRequest.base_url = PackageInstallRequest.base_url.replace(
        "/sobjects/", "/tooling/sobjects/"
    )
    request = PackageInstallRequest.create(
        {
            "EnableRss": options.get("activateRSS", True),
            "NameConflictResolution": options.get("name_conflict_resolution", "Block"),
            "Password": options.get("password"),
            "SecurityType": options.get("security_type", "FULL"),
            "SubscriberPackageVersionKey": options["version_id"],
        }
    )
    poll(functools.partial(_wait_for_package_install, tooling, request))


def _should_retry_package_install(err: Exception) -> bool:
    if isinstance(
        err, SalesforceMalformedRequest
    ) and "invalid cross reference id" in str(err):
        return True
    return False


def install_package_version(
    project_config, org_config, install_options, retry_options=None
):
    retry_options = {
        **(retry_options or {}),
        "should_retry": _should_retry_package_install,
    }
    retry(
        functools.partial(
            _install_package_version, project_config, org_config, install_options
        ),
        **retry_options,
    )

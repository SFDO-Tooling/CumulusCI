from cumulusci.core.exceptions import PackageInstallError
import logging

import pytest
import responses

from cumulusci.core.config import OrgConfig
from cumulusci.salesforce_api.package_install import (
    ManagedPackageInstallOptions,
    install_package_version,
)
from cumulusci.tests.util import create_project_config


@responses.activate
def test_install_package_version(caplog):
    caplog.set_level(logging.INFO)
    responses.add(
        "POST",
        "https://salesforce/services/data/v50.0/tooling/sobjects/PackageInstallRequest/",
        json={"id": "0Hf"},
    )
    responses.add(
        "GET",
        "https://salesforce/services/data/v50.0/tooling/query/",
        json={"records": [{"Status": "IN_PROGRESS"}]},
    )
    responses.add(
        "GET",
        "https://salesforce/services/data/v50.0/tooling/query/",
        json={"records": [{"Status": "SUCCESS"}]},
    )

    project_config = create_project_config()
    org_config = OrgConfig(
        {"instance_url": "https://salesforce", "access_token": "TOKEN"}, "test"
    )
    install_package_version(
        project_config, org_config, "04t", ManagedPackageInstallOptions()
    )
    assert "Success" in caplog.text


@responses.activate
def test_install_package_version__error():
    responses.add(
        "POST",
        "https://salesforce/services/data/v50.0/tooling/sobjects/PackageInstallRequest/",
        json={"id": "0Hf"},
    )
    responses.add(
        "GET",
        "https://salesforce/services/data/v50.0/tooling/query/",
        json={
            "records": [
                {
                    "Status": "ERROR",
                    "Errors": {"errors": [{"message": "We have a problem."}]},
                }
            ]
        },
    )

    project_config = create_project_config()
    org_config = OrgConfig(
        {"instance_url": "https://salesforce", "access_token": "TOKEN"}, "test"
    )
    with pytest.raises(PackageInstallError, match="We have a problem."):
        install_package_version(
            project_config, org_config, "04t", ManagedPackageInstallOptions()
        )


@responses.activate
def test_install_package_version__not_propagated(caplog):
    caplog.set_level(logging.INFO)
    responses.add(
        "POST",
        "https://salesforce/services/data/v50.0/tooling/sobjects/PackageInstallRequest/",
        json={"id": "0Hf"},
    )
    responses.add(
        "GET",
        "https://salesforce/services/data/v50.0/tooling/query/",
        status=400,
        body="invalid cross reference id",
    )
    responses.add(
        "GET",
        "https://salesforce/services/data/v50.0/tooling/query/",
        json={"records": [{"Status": "SUCCESS"}]},
    )

    project_config = create_project_config()
    org_config = OrgConfig(
        {"instance_url": "https://salesforce", "access_token": "TOKEN"}, "test"
    )
    install_package_version(
        project_config, org_config, "04t", ManagedPackageInstallOptions()
    )
    assert "Retrying" in caplog.text
    assert "Success" in caplog.text

import logging
from logging import getLogger
from unittest import mock

import pytest
import responses

from cumulusci.core.config import OrgConfig
from cumulusci.core.dependencies.utils import TaskContext
from cumulusci.core.exceptions import PackageInstallError
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.salesforce_api.package_install import (
    ApexCompileType,
    NameConflictResolution,
    PackageInstallOptions,
    SecurityType,
    UpgradeType,
    install_package_by_namespace_version,
    install_package_by_version_id,
)
from cumulusci.tests.util import CURRENT_SF_API_VERSION, create_project_config


@responses.activate
def test_install_package_by_version_id(caplog):
    caplog.set_level(logging.INFO)
    responses.add(
        "POST",
        f"https://salesforce/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/PackageInstallRequest/",
        json={"id": "0Hf"},
    )
    responses.add(
        "GET",
        f"https://salesforce/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/",
        json={"records": [{"Status": "IN_PROGRESS"}]},
    )
    responses.add(
        "GET",
        f"https://salesforce/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/",
        json={"records": [{"Status": "SUCCESS"}]},
    )

    project_config = create_project_config()
    org_config = OrgConfig(
        {"instance_url": "https://salesforce", "access_token": "TOKEN"}, "test"
    )
    install_package_by_version_id(
        project_config, org_config, "04t", PackageInstallOptions()
    )
    assert "Success" in caplog.text


@responses.activate
def test_install_package_by_version_id__error():
    responses.add(
        "POST",
        f"https://salesforce/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/PackageInstallRequest/",
        json={"id": "0Hf"},
    )
    responses.add(
        "GET",
        f"https://salesforce/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/",
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
        install_package_by_version_id(
            project_config, org_config, "04t", PackageInstallOptions()
        )


@responses.activate
def test_install_package_by_version_id__not_propagated(caplog):
    caplog.set_level(logging.INFO)
    responses.add(
        "POST",
        f"https://salesforce/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/PackageInstallRequest/",
        json={"id": "0Hf"},
    )
    responses.add(
        "GET",
        f"https://salesforce/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/",
        status=400,
        body="invalid cross reference id",
    )
    responses.add(
        "GET",
        f"https://salesforce/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/",
        json={"records": [{"Status": "SUCCESS"}]},
    )

    project_config = create_project_config()
    org_config = OrgConfig(
        {"instance_url": "https://salesforce", "access_token": "TOKEN"}, "test"
    )
    install_package_by_version_id(
        project_config, org_config, "04t", PackageInstallOptions()
    )
    assert "Retrying" in caplog.text
    assert "Success" in caplog.text


@mock.patch("cumulusci.salesforce_api.package_install.ApiDeploy")
@mock.patch("cumulusci.salesforce_api.package_install.InstallPackageZipBuilder")
def test_install_package_by_namespace_version(zip_builder, api_deploy):
    pc = mock.Mock()
    org = mock.Mock()

    install_package_by_namespace_version(
        pc,
        org,
        "foo",
        "1.0",
        PackageInstallOptions(
            activate_remote_site_settings=True,
            password="foobar",
            security_type=SecurityType.PUSH,
        ),
    )

    zip_builder.assert_called_once_with(
        namespace="foo",
        version="1.0",
        activateRSS=True,
        password="foobar",
        securityType="PUSH",
    )
    context = TaskContext(
        org_config=org,
        project_config=pc,
        logger=getLogger("cumulusci.salesforce_api.package_install"),
    )
    api_deploy.assert_called_once_with(context, mock.ANY, purge_on_delete=False)
    api_deploy.return_value.assert_called_once()


@mock.patch("cumulusci.salesforce_api.package_install.ApiDeploy")
@mock.patch("cumulusci.salesforce_api.package_install.InstallPackageZipBuilder")
def test_install_package_by_namespace_version__retry(zip_builder, api_deploy):
    pc = mock.Mock()
    org = mock.Mock()
    api_deploy.return_value.side_effect = [
        MetadataApiError("invalid cross reference id", None),
        None,
    ]

    install_package_by_namespace_version(
        pc,
        org,
        "foo",
        "1.0",
        PackageInstallOptions(),
    )

    context = TaskContext(
        org_config=org,
        project_config=pc,
        logger=getLogger("cumulusci.salesforce_api.package_install"),
    )
    api_deploy.assert_has_calls(
        [
            mock.call(context, mock.ANY, purge_on_delete=False),
            mock.call(context, mock.ANY, purge_on_delete=False),
        ],
        any_order=True,
    )

    api_deploy.return_value.assert_has_calls([mock.call(), mock.call()])


def test_package_install_options_from_task_options():
    task_options = {
        "activate_remote_site_settings": "False",
        "name_conflict_resolution": "RenameMetadata",
        "password": "foo",
        "security_type": "PUSH",
    }

    assert PackageInstallOptions.from_task_options(
        task_options
    ) == PackageInstallOptions(
        activate_remote_site_settings=False,
        name_conflict_resolution=NameConflictResolution.RENAME,
        password="foo",
        security_type=SecurityType.PUSH,
    )


def test_package_install_options_from_task_options__omitting_optionals():
    task_options = {
        "activate_remote_site_settings": "False",
        "name_conflict_resolution": "RenameMetadata",
        "password": "foo",
        "security_type": "PUSH",
        "apex_compile_type": "package",
        "upgrade_type": "deprecate-only",
    }

    assert PackageInstallOptions.from_task_options(
        task_options
    ) == PackageInstallOptions(
        activate_remote_site_settings=False,
        name_conflict_resolution=NameConflictResolution.RENAME,
        password="foo",
        security_type=SecurityType.PUSH,
        apex_compile_type=ApexCompileType.PACKAGE,
        upgrade_type=UpgradeType.DEPRECATE_ONLY,
    )

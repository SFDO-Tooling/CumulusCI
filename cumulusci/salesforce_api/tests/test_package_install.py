from collections import namedtuple
from cumulusci.core.dependencies.utils import TaskContext
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.core.exceptions import PackageInstallError
import logging
from unittest import mock

import pytest
import responses

from cumulusci.core.config import OrgConfig
from cumulusci.salesforce_api.package_install import (
    PackageInstallOptions,
    SecurityType,
    install_package_by_namespace_version,
    install_package_by_version_id,
)
from cumulusci.tests.util import create_project_config


@responses.activate
def test_install_package_by_version_id(caplog):
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
    install_package_by_version_id(
        project_config, org_config, "04t", PackageInstallOptions()
    )
    assert "Success" in caplog.text


@responses.activate
def test_install_package_by_version_id__error():
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
        install_package_by_version_id(
            project_config, org_config, "04t", PackageInstallOptions()
        )


@responses.activate
def test_install_package_by_version_id__not_propagated(caplog):
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

    task = TaskContext(org_config=org, project_config=pc, logger=mock.ANY)
    zip_builder.assert_called_once_with(
        namespace="foo",
        version="1.0",
        activateRSS=True,
        password="foobar",
        securityType="PUSH",
    )
    api_deploy.assert_called_once_with(task, mock.ANY, purge_on_delete=False)
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

    task = TaskContext(org_config=org, project_config=pc, logger=mock.ANY)
    api_deploy.assert_has_calls(
        [
            mock.call(task, mock.ANY, purge_on_delete=False),
            mock.call(task, mock.ANY, purge_on_delete=False),
        ],
        any_order=True,
    )

    api_deploy.return_value.assert_has_calls([mock.call(), mock.call()])

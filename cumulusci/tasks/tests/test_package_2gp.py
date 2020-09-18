from unittest import mock
import io
import json
import os
import pathlib
import shutil
import zipfile

import pytest
import responses
import yaml

from cumulusci.core.config import UniversalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.exceptions import DependencyLookupError
from cumulusci.core.exceptions import PackageUploadFailure
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.package_zip import BasePackageZipBuilder
from cumulusci.tasks.package_2gp import CreatePackageVersion
from cumulusci.tasks.package_2gp import VersionTypeEnum
from cumulusci.utils import temporary_dir
from cumulusci.utils import touch


@pytest.fixture
def repo_root():
    with temporary_dir() as path:
        os.mkdir(".git")
        os.mkdir("src")
        pathlib.Path(path, "src", "package.xml").write_text(
            '<?xml version="1.0" encoding="utf-8"?>\n<Package xmlns="http://soap.sforce.com/2006/04/metadata"></Package>'
        )
        with open("cumulusci.yml", "w") as f:
            yaml.dump(
                {
                    "project": {
                        "dependencies": [
                            {
                                "name": "EDA unpackaged/pre/first",
                                "repo_owner": "SalesforceFoundation",
                                "repo_name": "EDA",
                                "subfolder": "unpackaged/pre/first",
                            },
                            {
                                "namespace": "hed",
                                "version": "1.99",
                                "dependencies": [
                                    {"namespace": "pub", "version": "1.5"}
                                ],
                            },
                        ]
                    }
                },
                f,
            )
        pathlib.Path(path, "unpackaged", "pre", "first").mkdir(parents=True)
        touch(os.path.join("unpackaged", "pre", "first", "package.xml"))
        yield path


@pytest.fixture
def project_config(repo_root):
    project_config = BaseProjectConfig(
        UniversalConfig(), repo_info={"root": repo_root, "branch": "main"}
    )

    project_config.keychain = BaseProjectKeychain(project_config, key=None)
    pathlib.Path(repo_root, "orgs").mkdir()
    pathlib.Path(repo_root, "orgs", "scratch_def.json").write_text(
        json.dumps(
            {
                "edition": "Developer",
                "settings": {},
            }
        )
    )
    dev_org_config = OrgConfig({"config_file": "orgs/scratch_def.json"}, "dev")
    dependency_org_config = OrgConfig(
        {"instance_url": "https://test.salesforce.com", "access_token": "token"},
        "2gp_dependencies",
    )
    dependency_org_config._latest_api_version = "49.0"
    project_config.keychain.orgs = {
        "dev": dev_org_config,
        "2gp_dependencies": dependency_org_config,
    }

    project_config.get_github_api = mock.Mock()

    return project_config


@pytest.fixture
def org_config():
    org_config = OrgConfig(
        {"instance_url": "https://test.salesforce.com", "access_token": "token"}, "test"
    )
    org_config.refresh_oauth_token = mock.Mock()
    return org_config


@pytest.fixture
def task(project_config, org_config):
    task = CreatePackageVersion(
        project_config,
        TaskConfig(
            {
                "options": {
                    "package_type": "Unlocked",
                    "org_dependent": False,
                    "package_name": "Test Package",
                }
            }
        ),
        org_config,
    )
    task._init_task()
    return task


@pytest.fixture
def mock_download_extract_github():
    with mock.patch(
        "cumulusci.tasks.package_2gp.download_extract_github"
    ) as download_extract_github:
        yield download_extract_github


class TestCreatePackageVersion:
    base_url = "https://test.salesforce.com/services/data/v49.0"

    @responses.activate
    def test_run_task(self, task, mock_download_extract_github):
        mock_download_extract_github.return_value = zipfile.ZipFile(io.BytesIO(), "w")

        responses.add(  # query to find existing package
            "GET", f"{self.base_url}/tooling/query/", json={"size": 0, "records": []}
        )
        responses.add(  # create Package2
            "POST",
            f"{self.base_url}/tooling/sobjects/Package2/",
            json={"id": "0Ho6g000000fy4ZCAQ"},
        )
        responses.add(  # query to find existing package version
            "GET", f"{self.base_url}/tooling/query/", json={"size": 0, "records": []}
        )
        responses.add(  # query to find highest existing version
            "GET", f"{self.base_url}/tooling/query/", json={"size": 0, "records": []}
        )
        responses.add(  # query for dependency org installed packages
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "SubscriberPackage": {
                            "Id": "033000000000002AAA",
                            "NamespacePrefix": "pub",
                        },
                        "SubscriberPackageVersion": {
                            "Id": "04t000000000002AAA",
                            "MajorVersion": 1,
                            "MinorVersion": 5,
                            "PatchVersion": 0,
                            "BuildNumber": 1,
                            "IsBeta": False,
                        },
                    },
                    {
                        "SubscriberPackage": {
                            "Id": "033000000000003AAA",
                            "NamespacePrefix": "hed",
                        },
                        "SubscriberPackageVersion": {
                            "Id": "04t000000000003AAA",
                            "MajorVersion": 1,
                            "MinorVersion": 99,
                            "PatchVersion": 0,
                            "BuildNumber": 1,
                            "IsBeta": False,
                        },
                    },
                ],
            },
        )
        responses.add(  # query for existing package (dependency from github)
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {"Id": "0Ho000000000001AAA", "ContainerOptions": "Unlocked"}
                ],
            },
        )
        responses.add(  # query for existing package version (dependency from github)
            "GET",
            f"{self.base_url}/tooling/query/",
            json={"size": 1, "records": [{"Id": "08c000000000001AAA"}]},
        )
        responses.add(  # check status of Package2VersionCreateRequest (dependency from github)
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "Id": "08c000000000001AAA",
                        "Status": "Success",
                        "Package2VersionId": "051000000000001AAA",
                    }
                ],
            },
        )
        responses.add(  # get info from Package2Version (dependency from github)
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "SubscriberPackageVersionId": "04t000000000001AAA",
                        "MajorVersion": 0,
                        "MinorVersion": 1,
                        "PatchVersion": 0,
                        "BuildNumber": 1,
                    }
                ],
            },
        )
        responses.add(  # query for existing package (unpackaged/pre)
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {"Id": "0Ho000000000004AAA", "ContainerOptions": "Unlocked"}
                ],
            },
        )
        responses.add(  # query for existing package version (unpackaged/pre)
            "GET",
            f"{self.base_url}/tooling/query/",
            json={"size": 1, "records": [{"Id": "08c000000000004AAA"}]},
        )
        responses.add(  # check status of Package2VersionCreateRequest (unpackaged/pre)
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "Id": "08c000000000004AAA",
                        "Status": "Success",
                        "Package2VersionId": "051000000000004AAA",
                    }
                ],
            },
        )
        responses.add(  # get info from Package2Version (unpackaged/pre)
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "SubscriberPackageVersionId": "04t000000000004AAA",
                        "MajorVersion": 0,
                        "MinorVersion": 1,
                        "PatchVersion": 0,
                        "BuildNumber": 1,
                    }
                ],
            },
        )
        responses.add(  # create Package2VersionCreateRequest (main package)
            "POST",
            f"{self.base_url}/tooling/sobjects/Package2VersionCreateRequest/",
            json={"id": "08c000000000002AAA"},
        )
        responses.add(  # check status of Package2VersionCreateRequest (main package)
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "Id": "08c000000000002AAA",
                        "Status": "Success",
                        "Package2VersionId": "051000000000002AAA",
                    }
                ],
            },
        )
        responses.add(  # get info from Package2Version (main package)
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "SubscriberPackageVersionId": "04t000000000002AAA",
                        "MajorVersion": 1,
                        "MinorVersion": 0,
                        "PatchVersion": 0,
                        "BuildNumber": 1,
                    }
                ],
            },
        )
        responses.add(  # get dependencies from SubscriberPackageVersion (main package)
            "GET",
            f"{self.base_url}/tooling/query/",
            json={"size": 1, "records": [{"Dependencies": ""}]},
        )

        task.options["dependency_org"] = "2gp_dependencies"
        task()

    @responses.activate
    def test_get_or_create_package__namespaced_existing(
        self, project_config, org_config
    ):
        responses.add(  # query to find existing package
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {"Id": "0Ho6g000000fy4ZCAQ", "ContainerOptions": "Unlocked"}
                ],
            },
        )

        task = CreatePackageVersion(
            project_config,
            TaskConfig(
                {
                    "options": {
                        "package_type": "Unlocked",
                        "package_name": "Test Package",
                        "namespace": "ns",
                    }
                }
            ),
            org_config,
        )
        task._init_task()
        result = task._get_or_create_package(task.package_config)
        assert result == "0Ho6g000000fy4ZCAQ"

    @responses.activate
    def test_get_or_create_package__exists_but_wrong_type(
        self, project_config, org_config
    ):
        responses.add(  # query to find existing package
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {"Id": "0Ho6g000000fy4ZCAQ", "ContainerOptions": "Managed"}
                ],
            },
        )

        task = CreatePackageVersion(
            project_config,
            TaskConfig(
                {
                    "options": {
                        "package_type": "Unlocked",
                        "package_name": "Test Package",
                        "namespace": "ns",
                    }
                }
            ),
            org_config,
        )
        task._init_task()
        with pytest.raises(PackageUploadFailure):
            task._get_or_create_package(task.package_config)

    @responses.activate
    def test_get_or_create_package__devhub_disabled(self, task):
        responses.add(
            "GET",
            f"{self.base_url}/tooling/query/",
            json=[{"message": "Object type 'Package2' is not supported"}],
            status=400,
        )

        with pytest.raises(TaskOptionsError):
            task._get_or_create_package(task.package_config)

    @responses.activate
    def test_get_or_create_package__multiple_existing(self, task):
        responses.add(
            "GET", f"{self.base_url}/tooling/query/", json={"size": 2, "records": []}
        )

        with pytest.raises(TaskOptionsError):
            task._get_or_create_package(task.package_config)

    @responses.activate
    def test_create_version_request__existing_package_version(self, task):
        responses.add(
            "GET",
            f"{self.base_url}/tooling/query/",
            json={"size": 1, "records": [{"Id": "08c000000000001AAA"}]},
        )

        builder = BasePackageZipBuilder()
        result = task._create_version_request(
            "0Ho6g000000fy4ZCAQ", task.package_config, builder
        )
        assert result == "08c000000000001AAA"

    @responses.activate
    def test_get_highest_version_parts(self, task):
        responses.add(
            "GET",
            f"{self.base_url}/tooling/query/",
            json={"size": 1, "records": [{"MajorVersion": 1}]},
        )

        result = task._get_highest_version_parts("0Ho6g000000fy4ZCAQ")
        assert result == {"MajorVersion": 1}

    @responses.activate
    def test_get_next_version_number__major(self, task):
        result = task._get_next_version_number(
            {
                "MajorVersion": 0,
                "MinorVersion": 0,
                "PatchVersion": 0,
                "BuildNumber": 0,
                "IsReleased": True,
            },
            VersionTypeEnum.major,
        )
        assert result == "1.0.0.NEXT"

    @responses.activate
    def test_get_next_version_number__minor(self, task):
        result = task._get_next_version_number(
            {
                "MajorVersion": 0,
                "MinorVersion": 0,
                "PatchVersion": 0,
                "BuildNumber": 0,
                "IsReleased": True,
            },
            VersionTypeEnum.minor,
        )
        assert result == "0.1.0.NEXT"

    @responses.activate
    def test_get_next_version_number__patch(self, task):
        result = task._get_next_version_number(
            {
                "MajorVersion": 1,
                "MinorVersion": 0,
                "PatchVersion": 0,
                "BuildNumber": 0,
                "IsReleased": True,
            },
            VersionTypeEnum.patch,
        )
        assert result == "1.0.1.NEXT"

    def test_has_1gp_namespace_dependencies__no(self, task):
        assert not task._has_1gp_namespace_dependency([])

    def test_has_1gp_namespace_dependencies__transitive(self, task):
        assert task._has_1gp_namespace_dependency(
            [{"dependencies": [{"namespace": "foo", "version": "1.0"}]}]
        )

    @responses.activate
    def test_get_dependency_org__new_org(self, task):
        task.project_config.keychain.orgs = {}

        with mock.patch("cumulusci.core.flowrunner.FlowCoordinator.run") as flow_run:
            org = task._get_dependency_org()

        assert org.name == "2gp_dependencies"
        flow_run.assert_called_once()

    @responses.activate
    def test_get_dependency_org__expired(self, task):
        task.project_config.keychain.orgs[
            "2gp_dependencies"
        ].create_org = create_org = mock.Mock()
        task.project_config.keychain.orgs["2gp_dependencies"].config.update(
            {"created": True, "expired": True}
        )

        with mock.patch("cumulusci.core.flowrunner.FlowCoordinator.run") as flow_run:
            org = task._get_dependency_org()

        assert org.name == "2gp_dependencies"
        create_org.assert_called_once()
        flow_run.assert_called_once()

    @responses.activate
    def test_get_dependency_org__use_existing(self, task):
        task.project_config.keychain.orgs["2gp_dependencies"].config.update(
            {"created": True}
        )

        with mock.patch("cumulusci.core.flowrunner.FlowCoordinator.run") as flow_run:
            org = task._get_dependency_org()

        assert org.name == "2gp_dependencies"
        flow_run.assert_called_once()

    def test_convert_project_dependencies__unrecognized_format(self, task):
        with pytest.raises(DependencyLookupError):
            task._convert_project_dependencies([{"foo": "bar"}])

    def test_unpackaged_pre_dependencies__none(self, task):
        shutil.rmtree(str(pathlib.Path(task.project_config.repo_root, "unpackaged")))

        assert task._get_unpackaged_pre_dependencies([]) == []

    @responses.activate
    def test_poll_action__error(self, task):
        responses.add(
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Id": "08c000000000002AAA", "Status": "Error"}],
            },
        )
        responses.add(
            "GET",
            f"{self.base_url}/tooling/query/",
            json={"size": 1, "records": [{"Message": "message"}]},
        )

        task.request_id = "08c000000000002AAA"
        with pytest.raises(PackageUploadFailure) as err:
            task._poll_action()
        assert "message" in str(err)

    @responses.activate
    def test_poll_action__other(self, task):
        responses.add(
            "GET",
            f"{self.base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Id": "08c000000000002AAA", "Status": "InProgress"}],
            },
        )

        task.request_id = "08c000000000002AAA"
        task._poll_action()

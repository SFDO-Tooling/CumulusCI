import io
import json
import os
import pathlib
import re
import shutil
import zipfile
from unittest import mock

import pytest
import responses
import yaml
from pydantic import ValidationError

from cumulusci.core.config import BaseProjectConfig, TaskConfig, UniversalConfig
from cumulusci.core.dependencies.dependencies import (
    PackageNamespaceVersionDependency,
    PackageVersionIdDependency,
    UnmanagedGitHubRefDependency,
)
from cumulusci.core.exceptions import (
    CumulusCIUsageError,
    DependencyLookupError,
    GithubException,
    PackageUploadFailure,
    TaskOptionsError,
)
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.salesforce_api.package_zip import BasePackageZipBuilder
from cumulusci.tasks.create_package_version import (
    CreatePackageVersion,
    PackageConfig,
    PackageTypeEnum,
    VersionTypeEnum,
)
from cumulusci.utils import temporary_dir, touch


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
                            {"namespace": "pub", "version": "1.5"},
                            {
                                "repo_owner": "SalesforceFoundation",
                                "repo_name": "EDA",
                                "ref": "aaaaa",
                                "subfolder": "unpackaged/pre/first",
                            },
                            {
                                "namespace": "hed",
                                "version": "1.99",
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
        UniversalConfig(),
        repo_info={"root": repo_root, "branch": "main"},
    )
    project_config.config["project"]["package"]["install_class"] = "Install"
    project_config.config["project"]["package"]["uninstall_class"] = "Uninstall"
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

    project_config.get_github_api = mock.Mock()

    return project_config


@pytest.fixture
def get_task(project_config, devhub_config, org_config):
    def _get_task(options=None):
        opts = options or {
            "package_type": "Managed",
            "org_dependent": False,
            "package_name": "Test Package",
            "static_resource_path": "static-resources",
            "ancestor_id": "04t000000000000",
            "create_unlocked_dependency_packages": True,
            "install_key": "foo",
        }
        task = CreatePackageVersion(
            project_config,
            TaskConfig({"options": opts}),
            org_config,
        )
        with mock.patch(
            "cumulusci.tasks.create_package_version.get_devhub_config",
            return_value=devhub_config,
        ):
            task._init_task()
        return task

    return _get_task


@pytest.fixture
def task(get_task):
    return get_task()


@pytest.fixture
def mock_download_extract_github():
    with mock.patch(
        "cumulusci.core.dependencies.dependencies.download_extract_github_from_repo"
    ) as download_extract_github:
        yield download_extract_github


@pytest.fixture
def mock_get_static_dependencies():
    with mock.patch(
        "cumulusci.tasks.create_package_version.get_static_dependencies"
    ) as get_static_dependencies:
        get_static_dependencies.return_value = [
            PackageNamespaceVersionDependency(namespace="pub", version="1.5"),
            UnmanagedGitHubRefDependency(
                repo_owner="SalesforceFoundation",
                repo_name="EDA",
                subfolder="unpackaged/pre/first",
                ref="abcdef",
            ),
            PackageNamespaceVersionDependency(namespace="hed", version="1.99"),
        ]
        yield get_static_dependencies


class TestPackageConfig:
    def test_validate_org_dependent(self):
        with pytest.raises(ValidationError, match="Only unlocked packages"):
            PackageConfig(package_type=PackageTypeEnum.managed, org_dependent=True)  # type: ignore

    def test_validate_post_install_script(self):
        with pytest.raises(ValidationError, match="Only managed packages"):
            PackageConfig(
                package_type=PackageTypeEnum.unlocked, post_install_script="Install"
            )  # type: ignore

    def test_validate_uninstall_script(self):
        with pytest.raises(ValidationError, match="Only managed packages"):
            PackageConfig(
                package_type=PackageTypeEnum.unlocked, uninstall_script="Uninstall"
            )  # type: ignore


class TestCreatePackageVersion:
    devhub_base_url = "https://devhub.my.salesforce.com/services/data/v52.0"
    scratch_base_url = "https://scratch.my.salesforce.com/services/data/v52.0"

    def test_postinstall_script_logic(self, get_task):
        task = get_task({"package_type": "Managed", "package_name": "Foo"})

        # Values set in the fixture project_config above
        assert task.package_config.post_install_script == "Install"
        assert task.package_config.uninstall_script == "Uninstall"

        task = get_task(
            {
                "package_type": "Unlocked",
                "package_name": "Foo",
                "post_install_script": None,
                "uninstall_script": None,
            }
        )

        assert task.package_config.post_install_script is None
        assert task.package_config.uninstall_script is None

    @responses.activate
    def test_run_task(
        self,
        task,
        mock_download_extract_github,
        mock_get_static_dependencies,
        devhub_config,
    ):
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr("unpackaged/pre/first/package.xml", "")
        mock_download_extract_github.return_value = zf
        # _get_or_create_package() responses
        responses.add(  # query to find existing package
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 0, "records": []},
        )
        responses.add(  # create Package2
            "POST",
            f"{self.devhub_base_url}/tooling/sobjects/Package2/",
            json={"id": "0Ho6g000000fy4ZCAQ"},
        )

        # _resolve_ancestor_id() responses
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 1, "records": [{"Id": "05i000000000000"}]},
        )

        # _create_version_request() responses
        responses.add(  # query to find existing Package2VersionCreateRequest
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 0, "records": []},
        )
        responses.add(  # query to find base version
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "Id": "04t000000000002AAA",
                        "MajorVersion": 1,
                        "MinorVersion": 0,
                        "PatchVersion": 0,
                        "BuildNumber": 1,
                        "IsReleased": False,
                    }
                ],
            },
        )
        responses.add(  # get dependency org API version
            "GET",
            "https://scratch.my.salesforce.com/services/data",
            json=[{"version": "52.0"}],
        )
        responses.add(  # query for dependency org installed packages
            "GET",
            f"{self.scratch_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "SubscriberPackage": {
                            "Id": "033000000000002AAA",
                            "NamespacePrefix": "pub",
                        },
                        "SubscriberPackageVersionId": "04t000000000002AAA",
                    },
                    {
                        "SubscriberPackage": {
                            "Id": "033000000000003AAA",
                            "NamespacePrefix": "hed",
                        },
                        "SubscriberPackageVersionId": "04t000000000003AAA",
                    },
                ],
            },
        )
        responses.add(  # query dependency org for installed package 1)
            "GET",
            f"{self.scratch_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "Id": "04t000000000002AAA",
                        "MajorVersion": 1,
                        "MinorVersion": 5,
                        "PatchVersion": 0,
                        "BuildNumber": 1,
                        "IsBeta": False,
                    }
                ],
            },
        ),
        responses.add(  # query dependency org for installed package 2)
            "GET",
            f"{self.scratch_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "Id": "04t000000000003AAA",
                        "MajorVersion": 1,
                        "MinorVersion": 99,
                        "PatchVersion": 0,
                        "BuildNumber": 1,
                        "IsBeta": False,
                    }
                ],
            },
        )
        responses.add(  # query for existing package (dependency from github)
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {"Id": "0Ho000000000001AAA", "ContainerOptions": "Unlocked"}
                ],
            },
        )
        responses.add(  # query for existing package version (dependency from github)
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 1, "records": [{"Id": "08c000000000001AAA"}]},
        )
        responses.add(  # check status of Package2VersionCreateRequest (dependency from github)
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
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
            f"{self.devhub_base_url}/tooling/query/",
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
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {"Id": "0Ho000000000004AAA", "ContainerOptions": "Unlocked"}
                ],
            },
        )
        responses.add(  # query for existing package version (unpackaged/pre)
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 1, "records": [{"Id": "08c000000000004AAA"}]},
        )
        responses.add(  # check status of Package2VersionCreateRequest (unpackaged/pre)
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
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
            f"{self.devhub_base_url}/tooling/query/",
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
            f"{self.devhub_base_url}/tooling/sobjects/Package2VersionCreateRequest/",
            json={"id": "08c000000000002AAA"},
        )
        responses.add(  # check status of Package2VersionCreateRequest (main package)
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
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
            f"{self.devhub_base_url}/tooling/query/",
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
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "Dependencies": {
                            "ids": [
                                {"subscriberPackageVersionId": "04t000000000009AAA"}
                            ]
                        }
                    }
                ],
            },
        )

        with mock.patch(
            "cumulusci.tasks.create_package_version.get_devhub_config",
            return_value=devhub_config,
        ):
            task()

        assert task.return_values["dependencies"] == [
            {"version_id": "04t000000000009AAA"}
        ]
        zf.close()

    @responses.activate
    def test_get_or_create_package__namespaced_existing(
        self, project_config, devhub_config, org_config
    ):
        responses.add(  # query to find existing package
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
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
                        "package_type": "Managed",
                        "package_name": "Test Package",
                        "namespace": "ns",
                    }
                }
            ),
            org_config,
        )

        with mock.patch(
            "cumulusci.tasks.create_package_version.get_devhub_config",
            return_value=devhub_config,
        ):
            task._init_task()

        result = task._get_or_create_package(task.package_config)
        assert result == "0Ho6g000000fy4ZCAQ"

    @responses.activate
    def test_get_or_create_package__exists_but_wrong_type(
        self, project_config, devhub_config, org_config
    ):
        responses.add(  # query to find existing package
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
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
                        "package_type": "Managed",
                        "package_name": "Test Package",
                        "namespace": "ns",
                    }
                }
            ),
            org_config,
        )
        with mock.patch(
            "cumulusci.tasks.create_package_version.get_devhub_config",
            return_value=devhub_config,
        ):
            task._init_task()
        with pytest.raises(PackageUploadFailure):
            task._get_or_create_package(task.package_config)

    @responses.activate
    def test_get_or_create_package__devhub_disabled(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json=[{"message": "Object type 'Package2' is not supported"}],
            status=400,
        )

        with pytest.raises(TaskOptionsError):
            task._get_or_create_package(task.package_config)

    @responses.activate
    def test_get_or_create_package__multiple_existing(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 2, "records": []},
        )

        with pytest.raises(TaskOptionsError):
            task._get_or_create_package(task.package_config)

    @responses.activate
    def test_create_version_request__existing_package_version(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 1, "records": [{"Id": "08c000000000001AAA"}]},
        )

        builder = BasePackageZipBuilder()
        result = task._create_version_request(
            "0Ho6g000000fy4ZCAQ", task.package_config, builder
        )
        assert result == "08c000000000001AAA"

    def test_has_1gp_namespace_dependencies__no(self, task):
        assert not task._has_1gp_namespace_dependency([])

    def test_has_1gp_namespace_dependencies__transitive(self, task):
        assert task._has_1gp_namespace_dependency(
            [PackageNamespaceVersionDependency(namespace="foo", version="1.5")]
        )

    def test_convert_project_dependencies__unrecognized_format(self, task):
        with pytest.raises(DependencyLookupError):
            task._convert_project_dependencies([{"foo": "bar"}])

    def test_convert_project_dependencies__no_unlocked_packages(self, task):
        task.options["create_unlocked_dependency_packages"] = False
        assert task._convert_project_dependencies(
            [
                PackageVersionIdDependency(version_id="04t000000000000"),
                UnmanagedGitHubRefDependency(
                    github="https://github.com/test/test", ref="abcdef"
                ),
            ]
        ) == [{"subscriberPackageVersionId": "04t000000000000"}]

    def test_unpackaged_pre_dependencies__none(self, task):
        shutil.rmtree(str(pathlib.Path(task.project_config.repo_root, "unpackaged")))

        assert task._get_unpackaged_pre_dependencies([]) == []

    def test_unpackaged_pre_dependencies__no_unlocked_packages(self, task):
        task.options["create_unlocked_dependency_packages"] = False

        assert task._get_unpackaged_pre_dependencies([]) == []

    @responses.activate
    def test_poll_action__error(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Id": "08c000000000002AAA", "Status": "Error"}],
            },
        )
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
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
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Id": "08c000000000002AAA", "Status": "InProgress"}],
            },
        )

        task.request_id = "08c000000000002AAA"
        task._poll_action()

    @responses.activate
    def test_get_base_version_number__fallback(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 0, "records": []},
        )

        version = task._get_base_version_number(None, "0Ho6g000000fy4ZCAQ")
        assert version.format() == "0.0.0.0"

    @responses.activate
    def test_get_base_version_number__from_github(self, task):
        task.project_config.get_latest_version = mock.Mock(return_value="1.0.0.1")

        version = task._get_base_version_number(
            "latest_github_release", "0Ho6g000000fy4ZCAQ"
        )
        assert version.format() == "1.0.0.1"

    @responses.activate
    def test_get_base_version_number__from_github_1gp(self, task):
        task.project_config.get_latest_version = mock.Mock(return_value="1.0.0")

        version = task._get_base_version_number(
            "latest_github_release", "0Ho6g000000fy4ZCAQ"
        )
        assert version.format() == "1.0.0.0"

    @responses.activate
    def test_get_base_version_number__from_github_1gp_2_figures(self, task):
        task.project_config.get_latest_version = mock.Mock(return_value="1.0")

        version = task._get_base_version_number(
            "latest_github_release", "0Ho6g000000fy4ZCAQ"
        )
        assert version.format() == "1.0.0.0"

    @responses.activate
    def test_get_base_version_number__from_github_1gp_beta(self, task):
        # This shouldn't happen unless the project is misconfigured,
        # but we'll ensure we handle it gracefully.
        task.project_config.get_latest_version = mock.Mock(return_value="1.0 (Beta 2)")

        version = task._get_base_version_number(
            "latest_github_release", "0Ho6g000000fy4ZCAQ"
        )
        assert version.format() == "1.0.0.2"

    @responses.activate
    def test_get_base_version_number__from_github__no_release(self, task):
        task.project_config.get_latest_version = mock.Mock(side_effect=GithubException)

        version = task._get_base_version_number(
            "latest_github_release", "0Ho6g000000fy4ZCAQ"
        )
        assert version.format() == "0.0.0.0"

    @responses.activate
    def test_get_base_version_number__explicit(self, task):
        version = task._get_base_version_number("1.0.0.1", "0Ho6g000000fy4ZCAQ")
        assert version.format() == "1.0.0.1"

    @responses.activate
    def test_increment_major_version__no_version_base_specified(self, task):
        """Test incrementing version from 0.0.0.12 -> 1.0.0.0"""
        responses.add(  # query to find base version
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "Id": "04t000000000002AAA",
                        "MajorVersion": 0,
                        "MinorVersion": 0,
                        "PatchVersion": 0,
                        "BuildNumber": 12,
                        "IsReleased": False,
                    }
                ],
            },
        )
        version_base = None
        version = task._get_base_version_number(version_base, "a package 2 Id")
        next_version = version.increment(VersionTypeEnum.major)
        assert next_version.format() == "1.0.0.NEXT"

    @responses.activate
    @mock.patch("cumulusci.tasks.create_package_version.get_version_id_from_tag")
    def test_resolve_ancestor_id__latest_github_release(
        self, get_version_id_from_tag, task
    ):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 1, "records": [{"Id": "05i000000000000"}]},
        )

        project_config = mock.Mock()
        task.project_config = project_config

        get_version_id_from_tag.return_value = "04t000000000111"

        actual_id = task._resolve_ancestor_id("latest_github_release")
        assert actual_id == "05i000000000000"

    @responses.activate
    def test_resolve_ancestor_id__no_ancestor_specified(self, task):
        project_config = mock.Mock()
        project_config.get_latest_tag.side_effect = GithubException
        task.project_config = project_config

        assert task._resolve_ancestor_id() == ""

    @responses.activate
    @mock.patch("cumulusci.tasks.create_package_version.get_version_id_from_tag")
    def test_resolve_ancestor_id__ancestor_explicitly_specified(
        self, get_version_id_from_tag, task
    ):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 1, "records": [{"Id": "05i000000000000"}]},
        )

        project_config = mock.Mock()
        task.project_config = project_config

        get_version_id_from_tag.return_value = "04t000000000111"

        actual_id = task._resolve_ancestor_id("04t000000000000")
        assert actual_id == "05i000000000000"

    @responses.activate
    def test_resolve_ancestor_id__no_release_found(self, task):
        project_config = mock.Mock()
        project_config.get_latest_tag.side_effect = GithubException
        task.project_config = project_config

        assert task._resolve_ancestor_id("latest_github_release") == ""

    def test_resolve_ancestor_id__unlocked_package(self, task):
        task.package_config = PackageConfig(
            package_name="test_package",
            package_type="Unlocked",
            org_dependent=False,
            post_install_script=None,
            uninstall_script=None,
            namespace="test",
            version_name="Release",
            version_base=None,
            version_type="patch",
        )
        with pytest.raises(
            CumulusCIUsageError,
            match="Cannot specify an ancestor for Unlocked packages.",
        ):
            task._resolve_ancestor_id("04t000000000000")

    def test_resolve_ancestor_id__invalid_option_value(self, task):
        with pytest.raises(
            TaskOptionsError,
            match=re.escape("Unrecognized value for ancestor_id: 001001001001001"),
        ):
            task._resolve_ancestor_id("001001001001001")

    def test_prepare_cci_dependencies(self, task):
        assert task._prepare_cci_dependencies("") == []
        assert task._prepare_cci_dependencies(None) == []
        assert task._prepare_cci_dependencies(
            {"ids": [{"subscriberPackageVersionId": "04t000000000000"}]}
        ) == [{"version_id": "04t000000000000"}]

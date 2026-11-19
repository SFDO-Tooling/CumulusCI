import json
from unittest import mock

import pytest

from cumulusci.core.dependencies.dependencies import (
    GitHubDynamicDependency,
    PackageVersionIdDependency,
)
from cumulusci.core.dependencies.resolvers import get_static_dependencies
from cumulusci.core.exceptions import DependencyResolutionError, SfdxOrgException
from cumulusci.tests.util import create_project_config

PACKAGE_ID = "0Ho000000000001"
VERSION_ID = "04t000000000001"
OTHER_VERSION_ID = "04t000000000002"


@pytest.fixture
def config(tmp_path):
    config = create_project_config()
    config.repo_info["root"] = str(tmp_path)
    config.config["project"]["dependencies"] = [{"project": "sfdx-project.json"}]
    return config


def write_project(path, dependencies, **directory_options):
    path.write_text(
        json.dumps(
            {
                "packageAliases": {"Library": PACKAGE_ID, "Library@1": VERSION_ID},
                "packageDirectories": [
                    {
                        "path": "force-app",
                        "dependencies": dependencies,
                        **directory_options,
                    },
                    {
                        "path": "other-app",
                        "dependencies": [{"package": OTHER_VERSION_ID}],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    "version_number, scope, responses",
    [
        ("1.2.3.4", "Branch = 'feature'", []),
        ("1.2.3.LATEST", "Branch = 'feature'", [{"records": [{"expr0": 4}]}]),
        ("1.2.3.RELEASED", "IsReleased = true", [{"records": [{"expr0": 4}]}]),
    ],
)
def test_dynamic_version(config, tmp_path, version_number, scope, responses):
    write_project(
        tmp_path / "sfdx-project.json",
        [{"package": "Library", "versionNumber": version_number, "branch": "feature"}],
    )
    hub = mock.Mock()
    hub.query.side_effect = [
        *responses,
        {"records": [{"SubscriberPackageVersionId": VERSION_ID}]},
    ]
    with (
        mock.patch(
            "cumulusci.core.dependencies.sfdx_project.get_devhub_config"
        ) as devhub,
        mock.patch(
            "cumulusci.core.dependencies.sfdx_project.get_simple_salesforce_connection",
            return_value=hub,
        ) as connection,
    ):
        assert get_static_dependencies(config, strategies=[]) == [
            PackageVersionIdDependency(version_id=VERSION_ID),
            PackageVersionIdDependency(version_id=OTHER_VERSION_ID),
        ]
    connection.assert_called_once_with(config, devhub.return_value, base_url="tooling")
    queries = [call.args[0] for call in hub.query.call_args_list]
    assert all(scope in query for query in queries)
    assert "BuildNumber = 4" in queries[-1]
    assert "PatchVersion = 3" in queries[-1]
    if responses:
        assert "MAX(BuildNumber)" in queries[0]
        assert "IsDeprecated != true" in queries[0]


def test_version_aliases_and_duplicates_require_no_dev_hub(config, tmp_path):
    write_project(
        tmp_path / "sfdx-project.json",
        [{"package": "Library@1"}, {"subscriberPackageVersionId": VERSION_ID}],
    )
    config.config["project"]["dependencies"] = [
        {"version_id": VERSION_ID},
        {"project": "sfdx-project.json", "package_directory": "force-app"},
        {"project": "sfdx-project.json", "package_directory": "other-app"},
    ]
    with mock.patch(
        "cumulusci.core.dependencies.sfdx_project.get_devhub_config"
    ) as devhub:
        assert get_static_dependencies(config, strategies=[]) == [
            PackageVersionIdDependency(version_id=VERSION_ID),
            PackageVersionIdDependency(version_id=OTHER_VERSION_ID),
        ]
    devhub.assert_not_called()


@pytest.mark.parametrize(
    "declaration, expected",
    [
        ({"package": "unknown"}, "alias for one in packageAliases"),
        ({"package": PACKAGE_ID}, "needs versionNumber"),
        ({"package": PACKAGE_ID, "versionNumber": "1.0.0.NEXT"}, "needs versionNumber"),
        ({"package": PACKAGE_ID, "versionNumber": "1.0.0.LATEST"}, "No eligible"),
    ],
)
def test_resolution_failures(config, tmp_path, declaration, expected):
    write_project(tmp_path / "sfdx-project.json", [declaration])
    with (
        mock.patch("cumulusci.core.dependencies.sfdx_project.get_devhub_config"),
        mock.patch(
            "cumulusci.core.dependencies.sfdx_project.get_simple_salesforce_connection"
        ) as connection,
    ):
        connection.return_value.query.return_value = {"records": [{"expr0": None}]}
        with pytest.raises(DependencyResolutionError, match=expected):
            get_static_dependencies(config, strategies=[])


def test_conflicting_package_versions(config, tmp_path):
    write_project(
        tmp_path / "sfdx-project.json",
        [
            {"packageId": PACKAGE_ID, "versionNumber": "1.0.0.1"},
            {"packageId": PACKAGE_ID, "versionNumber": "1.0.0.2"},
        ],
    )
    with (
        mock.patch("cumulusci.core.dependencies.sfdx_project.get_devhub_config"),
        mock.patch(
            "cumulusci.core.dependencies.sfdx_project.get_simple_salesforce_connection"
        ) as connection,
    ):
        connection.return_value.query.side_effect = [
            {"records": [{"SubscriberPackageVersionId": version}]}
            for version in (VERSION_ID, OTHER_VERSION_ID)
        ]
        with pytest.raises(DependencyResolutionError, match="Conflicting versions"):
            get_static_dependencies(config, strategies=[])


def test_missing_project_file(config):
    with pytest.raises(
        DependencyResolutionError, match="Cannot read Salesforce DX project"
    ):
        get_static_dependencies(config, strategies=[])


def test_duplicate_keeps_explicit_install_options_at_first_position(config, tmp_path):
    write_project(tmp_path / "sfdx-project.json", [{"package": "Library@1"}])
    config.config["project"]["dependencies"].append(
        {"version_id": VERSION_ID, "password_env_name": "LIBRARY_INSTALL_KEY"}
    )
    assert get_static_dependencies(config, strategies=[]) == [
        PackageVersionIdDependency(
            version_id=VERSION_ID, password_env_name="LIBRARY_INSTALL_KEY"
        ),
        PackageVersionIdDependency(version_id=OTHER_VERSION_ID),
    ]


def test_inaccessible_dev_hub(config, tmp_path):
    write_project(
        tmp_path / "sfdx-project.json",
        [{"package": PACKAGE_ID, "versionNumber": "1.0.0.LATEST"}],
    )
    with (
        mock.patch(
            "cumulusci.core.dependencies.sfdx_project.get_devhub_config",
            side_effect=SfdxOrgException("No sf config found for target-dev-hub"),
        ),
        pytest.raises(
            DependencyResolutionError, match="Check Salesforce CLI authentication"
        ),
    ):
        get_static_dependencies(config, strategies=[])


def test_latest_inherits_branch_and_falls_back_when_missing(config, tmp_path):
    write_project(
        tmp_path / "sfdx-project.json",
        [{"package": PACKAGE_ID, "versionNumber": "1.0.0.LATEST"}],
        branch="feature",
    )
    hub = mock.Mock()
    hub.query.side_effect = [
        {"records": [{"expr0": None}]},
        {"records": [{"expr0": 2}]},
        {"records": [{"SubscriberPackageVersionId": VERSION_ID}]},
    ]
    with (
        mock.patch("cumulusci.core.dependencies.sfdx_project.get_devhub_config"),
        mock.patch(
            "cumulusci.core.dependencies.sfdx_project.get_simple_salesforce_connection",
            return_value=hub,
        ),
    ):
        get_static_dependencies(config, strategies=[])
    first, second, third = [call.args[0] for call in hub.query.call_args_list]
    assert "Branch = 'feature'" in first
    assert "Branch = null" in second
    assert "Branch = null" in third


def test_transitive_project_uses_upstream_ref(config, tmp_path):
    source = tmp_path / "upstream.json"
    write_project(source, [{"package": VERSION_ID}])
    upstream = create_project_config()
    upstream.config["project"]["dependencies"] = [
        {"project": "packages/sfdx-project.json"}
    ]
    repository = mock.Mock()
    repository.directory_contents.return_value = {}
    repository.file_contents.return_value.decoded = source.read_bytes()
    github_version = PackageVersionIdDependency(version_id="04t000000000009")
    dependency = GitHubDynamicDependency(
        github="https://github.com/owner/upstream",
    )
    dependency.ref = "upstream-sha"
    dependency.package_dependency = github_version
    with (
        mock.patch(
            "cumulusci.core.dependencies.dependencies.get_repo",
            return_value=repository,
        ),
        mock.patch(
            "cumulusci.core.dependencies.dependencies.get_remote_project_config",
            return_value=upstream,
        ),
    ):
        assert get_static_dependencies(config, [dependency], strategies=[]) == [
            PackageVersionIdDependency(version_id=VERSION_ID),
            PackageVersionIdDependency(version_id=OTHER_VERSION_ID),
            github_version,
        ]
    repository.file_contents.assert_called_once_with(
        "packages/sfdx-project.json", ref="upstream-sha"
    )

import os
from pathlib import Path
from unittest import mock

import click
import pytest

from cumulusci.cli.tests.utils import recursive_list_files, run_click_command
from cumulusci.core.dependencies.dependencies import PackageNamespaceVersionDependency
from cumulusci.core.exceptions import NotInProject
from cumulusci.utils import temporary_dir

from .. import project
from ..runtime import CliRuntime


class TestProjectCommands:
    def test_validate_project_name(self):
        with pytest.raises(click.UsageError):
            project.validate_project_name("with spaces")

    def test_validate_project_name__valid(self):
        assert project.validate_project_name("valid") == "valid"

    @mock.patch("cumulusci.cli.project.click")
    def test_project_init(self, click):
        with temporary_dir():
            os.mkdir(".git")
            Path(".git", "HEAD").write_text("ref: refs/heads/main")

            click.prompt.side_effect = (
                "testproj",  # project_name
                "testpkg",  # package_name
                "testns",  # package_namespace
                "43.0",  # api_version
                "mdapi",  # source_format
                "3",  # extend other URL
                "https://github.com/SalesforceFoundation/NPSP",  # github_url
                "main",  # git_default_branch
                "work/",  # git_prefix_feature
                "uat/",  # git_prefix_beta
                "rel/",  # git_prefix_release
                "%_TEST%",  # test_name_match
                "90",  # code_coverage
            )
            click.confirm.side_effect = (
                True,
                True,
                True,
            )  # is managed? extending? enforce Apex coverage?

            runtime = CliRuntime(
                config={"project": {"test": {"name_match": "%_TEST%"}}},
                load_keychain=False,
            )
            run_click_command(project.project_init, runtime=runtime)

            # Make sure expected files/dirs were created
            assert [
                ".git/",
                ".git/HEAD",
                ".github/",
                ".github/PULL_REQUEST_TEMPLATE.md",
                ".gitignore",
                "README.md",
                "cumulusci.yml",
                "datasets/",
                "datasets/mapping.yml",
                "orgs/",
                "orgs/beta.json",
                "orgs/dev.json",
                "orgs/feature.json",
                "orgs/release.json",
                "robot/",
                "robot/testproj/",
                "robot/testproj/doc/",
                "robot/testproj/resources/",
                "robot/testproj/tests/",
                "robot/testproj/tests/create_contact.robot",
                "sfdx-project.json",
                "src/",
            ] == recursive_list_files()

    @mock.patch("cumulusci.cli.project.click")
    def test_project_init_tasks(self, click):
        """Verify that the generated cumulusci.yml file is readable and has the proper robot task"""
        with temporary_dir():
            os.mkdir(".git")
            Path(".git", "HEAD").write_text("ref: refs/heads/main")

            click.prompt.side_effect = (
                "testproj",  # project_name
                "testpkg",  # package_name
                "testns",  # package_namespace
                "43.0",  # api_version
                "mdapi",  # source_format
                "3",  # extend other URL
                "https://github.com/SalesforceFoundation/NPSP",  # github_url
                "main",  # git_default_branch
                "work/",  # git_prefix_feature
                "uat/",  # git_prefix_beta
                "rel/",  # git_prefix_release
                "%_TEST%",  # test_name_match
                "90",  # code_coverage
            )
            click.confirm.side_effect = (
                True,
                True,
                True,
            )  # is managed? extending? enforce code coverage?

            run_click_command(project.project_init)

            # verify we can load the generated yml
            cli_runtime = CliRuntime(load_keychain=False)

            # ...and verify it has the expected tasks
            config = cli_runtime.project_config.config_project
            expected_tasks = {
                "robot": {
                    "options": {
                        "suites": "robot/testproj/tests",
                        "options": {"outputdir": "robot/testproj/results"},
                    }
                },
                "robot_testdoc": {
                    "options": {
                        "path": "robot/testproj/tests",
                        "output": "robot/testproj/doc/testproj_tests.html",
                    }
                },
                "run_tests": {"options": {"required_org_code_coverage_percent": 90}},
            }
            assert config["tasks"] == expected_tasks

    def test_project_init_no_git(self):
        with temporary_dir():
            with pytest.raises(click.ClickException):
                run_click_command(project.project_init)

    def test_project_init_already_initted(self):
        with temporary_dir():
            os.mkdir(".git")
            Path(".git", "HEAD").write_text("ref: refs/heads/main")
            with open("cumulusci.yml", "w"):
                pass  # create empty file

            with pytest.raises(click.ClickException):
                run_click_command(project.project_init)

    def test_project_init_dont_overwrite(self):
        with temporary_dir():
            # Gotta have a Repo
            os.mkdir(".git")
            Path(".git", "HEAD").write_text("ref: refs/heads/main")

            os.mkdir("orgs")
            orgs = "orgs/"
            text = "Can't touch this"

            path_list = [
                Path("README.md"),
                Path(".gitignore"),
                Path(orgs + "dev.json"),
                Path(orgs + "release.json"),
            ]
            for path in path_list:
                path.write_text(text)

            runtime = mock.Mock()
            runtime.project_config.project = {"test": "test"}

            run_click_command(project.project_info, runtime=runtime)

            # Project init must not overwrite project files or org defs
            for path in path_list:
                assert text == path.read_text()

    @mock.patch("click.echo")
    def test_project_info(self, echo):
        runtime = mock.Mock()
        runtime.project_config.project = {"test": "test"}

        run_click_command(project.project_info, runtime=runtime)

        echo.assert_called_once_with("\x1b[1mtest:\x1b[0m test")

    def test_project_info__outside_project(self):
        runtime = mock.Mock()
        runtime.project_config = None
        runtime.project_config_error = NotInProject()
        with temporary_dir():
            with pytest.raises(NotInProject):
                run_click_command(project.project_info, runtime=runtime)

    @mock.patch("cumulusci.cli.project.get_static_dependencies")
    def test_project_dependencies(self, get_static_dependencies):
        out = []
        runtime = mock.Mock()
        runtime.project_config.project__dependencies = [
            {"namespace": "npe01", "version": "3.16"},
            {"namespace": "npsp", "version": "3.193"},
        ]
        get_static_dependencies.return_value = [
            PackageNamespaceVersionDependency(namespace="npe01", version="3.16"),
            PackageNamespaceVersionDependency(namespace="npsp", version="3.193"),
        ]

        with mock.patch("click.echo", out.append):
            run_click_command(
                project.project_dependencies,
                runtime=runtime,
                resolution_strategy="production",
            )

        assert out == [
            str(PackageNamespaceVersionDependency(namespace="npe01", version="3.16")),
            str(PackageNamespaceVersionDependency(namespace="npsp", version="3.193")),
        ]

    def test_render_recursive(self):
        out = []
        with mock.patch("click.echo", out.append):
            project.render_recursive(
                {"test": [{"list": ["list"], "dict": {"key": "value"}, "str": "str"}]}
            )
        assert """\x1b[1mtest:\x1b[0m
    -
        \x1b[1mlist:\x1b[0m
            - list
        \x1b[1mdict:\x1b[0m
            \x1b[1mkey:\x1b[0m value
        \x1b[1mstr:\x1b[0m str""" == "\n".join(
            out
        )

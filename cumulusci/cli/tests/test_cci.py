# -*- coding: utf-8 -*-
from datetime import date
from datetime import datetime
from datetime import timedelta
import io
import json
import os
import shutil
import tempfile
import time
import pytest
import unittest
from pathlib import Path

import click
from unittest import mock
import pkg_resources
import requests
import responses
import github3
from requests.exceptions import ConnectionError

import cumulusci
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.tasks import BaseTask
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.core.exceptions import FlowNotFoundError
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import ScratchOrgException
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.cli import cci
from cumulusci.cli.runtime import CliRuntime
from cumulusci.utils import temporary_dir


def run_click_command(cmd, *args, **kw):
    """Run a click command with a mock context and injected CCI runtime object.
    """
    runtime = kw.pop("runtime", mock.Mock())
    with mock.patch("cumulusci.cli.cci.RUNTIME", runtime):
        with click.Context(command=mock.Mock()):
            return cmd.callback(*args, **kw)


def recursive_list_files(d="."):
    result = []
    for d, subdirs, files in os.walk(d):
        d = d.replace(os.path.sep, "/")
        if d != ".":
            result.append("/".join([d, ""])[2:])
        for f in files:
            result.append("/".join([d, f])[2:])
    result.sort()
    return result


class TestCCI(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.tempdir = tempfile.mkdtemp()
        os.environ["HOME"] = self.tempdir
        os.environ["CUMULUSCI_KEY"] = ""

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.tempdir)

    def test_get_installed_version(self):
        result = cci.get_installed_version()
        self.assertEqual(cumulusci.__version__, str(result))

    @responses.activate
    def test_get_latest_final_version(self):
        responses.add(
            method="GET",
            url="https://pypi.org/pypi/cumulusci/json",
            body=json.dumps(
                {
                    "releases": {
                        "1.0b1": {},
                        "1.0": {},
                        "1.0.1.dev0": {},
                        "1.0.1": {},
                        "1.0.post1": {},
                    }
                }
            ),
            status=200,
        )
        result = cci.get_latest_final_version()
        self.assertEqual("1.0.1", result.base_version)

    @mock.patch("cumulusci.cli.cci.get_installed_version")
    @mock.patch("cumulusci.cli.cci.get_latest_final_version")
    @mock.patch("cumulusci.cli.cci.click")
    def test_check_latest_version(
        self, click, get_latest_final_version, get_installed_version
    ):
        with cci.timestamp_file() as f:
            f.write(str(time.time() - 4000))
        get_latest_final_version.return_value = pkg_resources.parse_version("2")
        get_installed_version.return_value = pkg_resources.parse_version("1")

        cci.check_latest_version()

        self.assertEqual(2, click.echo.call_count)

    @mock.patch("cumulusci.cli.cci.get_latest_final_version")
    @mock.patch("cumulusci.cli.cci.click")
    def test_check_latest_version_request_error(self, click, get_latest_final_version):
        with cci.timestamp_file() as f:
            f.write(str(time.time() - 4000))
        get_latest_final_version.side_effect = requests.exceptions.RequestException()

        cci.check_latest_version()

        click.echo.assert_any_call("Error checking cci version:")

    def test_render_recursive(self):
        out = []
        with mock.patch("click.echo", out.append):
            cci.render_recursive(
                {"test": [{"list": ["list"], "dict": {"key": "value"}, "str": "str"}]}
            )
        self.assertEqual(
            """\x1b[1mtest:\x1b[0m
    -
        \x1b[1mlist:\x1b[0m
            - list
        \x1b[1mdict:\x1b[0m
            \x1b[1mkey:\x1b[0m value
        \x1b[1mstr:\x1b[0m str""",
            "\n".join(out),
        )

    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.init_logger")
    @mock.patch("cumulusci.cli.cci.check_latest_version")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    @mock.patch("cumulusci.cli.cci.cli")
    def test_main(
        self,
        cli,
        CliRuntime,
        check_latest_version,
        init_logger,
        get_tempfile_logger,
        tee,
    ):
        get_tempfile_logger.return_value = mock.Mock(), "tempfile.log"
        cci.main()

        check_latest_version.assert_called_once()
        init_logger.assert_called_once()
        CliRuntime.assert_called_once()
        cli.assert_called_once()
        tee.assert_called_once()

    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.init_logger")
    @mock.patch("cumulusci.cli.cci.check_latest_version")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    @mock.patch("cumulusci.cli.cci.cli")
    @mock.patch("pdb.post_mortem")
    @mock.patch("sys.exit")
    def test_main__debug(
        self,
        sys_exit,
        post_mortem,
        cli,
        CliRuntime,
        check_latest_version,
        init_logger,
        get_tempfile_logger,
        tee,
    ):
        cli.side_effect = Exception
        get_tempfile_logger.return_value = (mock.Mock(), "tempfile.log")

        cci.main(["cci", "--debug"])

        check_latest_version.assert_called_once()
        init_logger.assert_called_once_with(log_requests=True)
        CliRuntime.assert_called_once()
        cli.assert_called_once()
        post_mortem.assert_called_once()
        sys_exit.assert_called_once_with(1)
        get_tempfile_logger.assert_called_once()
        tee.assert_called_once()

    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.init_logger")
    @mock.patch("cumulusci.cli.cci.cli")
    @mock.patch("sys.exit")
    def test_main__abort(
        self, sys_exit, cli, init_logger, get_tempfile_logger, tee_stdout_stderr
    ):
        get_tempfile_logger.return_value = (mock.Mock(), "tempfile.log")
        cli.side_effect = click.Abort
        cci.main(["cci"])
        cli.assert_called_once()
        sys_exit.assert_called_once_with(1)

    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("cumulusci.cli.cci.CCI_LOGFILE_PATH")
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.init_logger")
    @mock.patch("cumulusci.cli.cci.check_latest_version")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    @mock.patch("cumulusci.cli.cci.cli")
    @mock.patch("pdb.post_mortem")
    @mock.patch("sys.exit")
    def test_main__error(
        self,
        sys_exit,
        post_mortem,
        cli,
        CliRuntime,
        check_latest_version,
        init_logger,
        get_tempfile_logger,
        logfile_path,
        tee,
    ):
        expected_logfile_content = "Hello there, I'm a logfile."
        logfile_path.is_file.return_value = True
        logfile_path.read_text.return_value = expected_logfile_content

        cli.side_effect = Exception
        get_tempfile_logger.return_value = mock.Mock(), "tempfile.log"

        cci.main(["cci", "org", "info"])

        check_latest_version.assert_called_once()
        init_logger.assert_called_once_with(log_requests=False)
        CliRuntime.assert_called_once()
        cli.assert_called_once()
        post_mortem.call_count == 0
        sys_exit.assert_called_once_with(1)
        get_tempfile_logger.assert_called_once()
        tee.assert_called_once()

        os.remove("tempfile.log")

    @mock.patch("cumulusci.cli.cci.open")
    @mock.patch("cumulusci.cli.cci.traceback")
    @mock.patch("cumulusci.cli.cci.click.style")
    def test_handle_exception(self, style, traceback, cci_open):
        logfile_path = "file.log"
        Path(logfile_path).touch()

        error = "Something bad happened."
        cci_open.__enter__.return_value = mock.Mock()

        cci.handle_exception(error, False, logfile_path)

        style.call_args_list[0][0] == f"Error: {error}"
        style.call_args_list[1][0] == cci.SUGGEST_ERROR_COMMAND
        traceback.print_exc.assert_called_once()

        os.remove(logfile_path)

    @mock.patch("cumulusci.cli.cci.open")
    @mock.patch("cumulusci.cli.cci.traceback")
    @mock.patch("cumulusci.cli.cci.click.style")
    def test_handle_exception__error_cmd(self, style, traceback, cci_open):
        """Ensure we don't write to logfiles when running `cci error ...` commands."""
        error = "Something bad happened."
        logfile_path = None
        cci.handle_exception(error, False, logfile_path)

        style.call_args_list[0][0] == f"Error: {error}"
        style.call_args_list[1][0] == cci.SUGGEST_ERROR_COMMAND
        assert not cci_open.called

    @mock.patch("cumulusci.cli.cci.open")
    @mock.patch("cumulusci.cli.cci.traceback")
    @mock.patch("cumulusci.cli.cci.click.style")
    def test_handle_click_exception(self, style, traceback, cci_open):
        logfile_path = "file.log"
        Path(logfile_path).touch()
        cci_open.__enter__.return_value = mock.Mock()

        cci.handle_exception(click.ClickException("oops"), False, logfile_path)
        style.call_args_list[0][0] == f"Error: oops"

        os.remove(logfile_path)

    @mock.patch("cumulusci.cli.cci.open")
    @mock.patch("cumulusci.cli.cci.connection_error_message")
    def test_handle_connection_exception(self, connection_msg, cci_open):
        logfile_path = "file.log"
        Path(logfile_path).touch()

        cci.handle_exception(ConnectionError(), False, logfile_path)
        connection_msg.assert_called_once()
        os.remove(logfile_path)

    @mock.patch("cumulusci.cli.cci.click.style")
    def test_connection_exception_message(self, style):
        cci.connection_error_message()
        style.assert_called_once_with(
            (
                f"We encountered an error with your internet connection. "
                "Please check your connection and try the last cci command again."
            ),
            fg="red",
        )

    @mock.patch("cumulusci.cli.cci.CCI_LOGFILE_PATH")
    @mock.patch("cumulusci.cli.cci.webbrowser")
    @mock.patch("cumulusci.cli.cci.platform")
    @mock.patch("cumulusci.cli.cci.sys")
    @mock.patch("cumulusci.cli.cci.datetime")
    @mock.patch("cumulusci.cli.cci.create_gist")
    @mock.patch("cumulusci.cli.cci.get_github_api")
    def test_gist(
        self, gh_api, create_gist, date, sys, platform, webbrowser, logfile_path
    ):

        platform.uname.return_value = mock.Mock(system="Rossian", machine="x68_46")
        sys.version = "1.0.0 (default Jul 24 2019)"
        sys.executable = "User/bob.ross/.pyenv/versions/cci-374/bin/python"
        date.utcnow.return_value = "01/01/1970"
        gh_api.return_value = mock.Mock()
        expected_gist_url = "https://gist.github.com/1234567890abcdefghijkl"
        create_gist.return_value = mock.Mock(html_url=expected_gist_url)

        expected_logfile_content = "Hello there, I'm a logfile."
        logfile_path.is_file.return_value = True
        logfile_path.read_text.return_value = expected_logfile_content

        runtime = mock.Mock()
        runtime.project_config.repo_root = None
        runtime.keychain.get_service.return_value.config = {
            "username": "usrnm",
            "password": "pwd",
        }

        run_click_command(cci.gist, runtime=runtime)

        expected_content = f"""CumulusCI version: {cumulusci.__version__}
Python version: {sys.version.split()[0]} ({sys.executable})
Environment Info: Rossian / x68_46
\n\nLast Command Run
================================
{expected_logfile_content}"""

        expected_files = {"cci_output_01/01/1970.txt": {"content": expected_content}}

        create_gist.assert_called_once_with(
            gh_api(), "CumulusCI Error Output", expected_files
        )
        webbrowser.open.assert_called_once_with(expected_gist_url)

    @mock.patch("cumulusci.cli.cci.CCI_LOGFILE_PATH")
    @mock.patch("cumulusci.cli.cci.click")
    @mock.patch("cumulusci.cli.cci.platform")
    @mock.patch("cumulusci.cli.cci.sys")
    @mock.patch("cumulusci.cli.cci.datetime")
    @mock.patch("cumulusci.cli.cci.create_gist")
    @mock.patch("cumulusci.cli.cci.get_github_api")
    def test_gist__creation_error(
        self, gh_api, create_gist, date, sys, platform, click, logfile_path
    ):

        expected_logfile_content = "Hello there, I'm a logfile."
        logfile_path.is_file.return_value = True
        logfile_path.read_text.return_value = expected_logfile_content

        platform.uname.return_value = mock.Mock(sysname="Rossian", machine="x68_46")
        sys.version = "1.0.0 (default Jul 24 2019)"
        sys.executable = "User/bob.ross/.pyenv/versions/cci-374/bin/python"
        date.utcnow.return_value = "01/01/1970"
        gh_api.return_value = mock.Mock()

        class ExceptionWithResponse(Exception, mock.Mock):
            def __init__(self, status_code):
                self.response = mock.Mock(status_code=status_code)

        create_gist.side_effect = ExceptionWithResponse(503)

        runtime = mock.Mock()
        runtime.project_config.repo_root = None
        runtime.keychain.get_service.return_value.config = {
            "username": "usrnm",
            "password": "pwd",
        }

        with self.assertRaises(CumulusCIException) as context:
            run_click_command(cci.gist, runtime=runtime)
        assert (
            "An error occurred attempting to create your gist"
            in context.exception.args[0]
        )

        class GitHubExceptionWithResponse(github3.exceptions.NotFoundError, mock.Mock):
            def __init__(self, status_code):
                self.response = mock.Mock(status_code=status_code)

        create_gist.side_effect = GitHubExceptionWithResponse(404)
        with self.assertRaises(CumulusCIException) as context:
            run_click_command(cci.gist, runtime=runtime)
        assert cci.GIST_404_ERR_MSG in context.exception.args[0]

    @mock.patch("cumulusci.cli.cci.CCI_LOGFILE_PATH")
    @mock.patch("cumulusci.cli.cci.click")
    @mock.patch("cumulusci.cli.cci.os")
    @mock.patch("cumulusci.cli.cci.datetime")
    @mock.patch("cumulusci.cli.cci.create_gist")
    @mock.patch("cumulusci.cli.cci.get_github_api")
    def test_gist__file_not_found(
        self, gh_api, create_gist, date, os, click, logfile_path
    ):
        logfile_path.is_file.return_value = False
        with pytest.raises(CumulusCIException):
            run_click_command(cci.gist)

    def test_cli(self):
        run_click_command(cci.cli)

    @mock.patch(
        "cumulusci.cli.cci.get_latest_final_version",
        mock.Mock(return_value=pkg_resources.parse_version("100")),
    )
    @mock.patch("click.echo")
    def test_version(self, echo):
        run_click_command(cci.version)
        assert cumulusci.__version__ in echo.call_args_list[1][0][0]

    @mock.patch(
        "cumulusci.cli.cci.get_latest_final_version",
        mock.Mock(return_value=pkg_resources.parse_version("100")),
    )
    @mock.patch("click.echo")
    def test_version__latest(self, echo):
        with mock.patch(
            "cumulusci.cli.cci.get_latest_final_version", cci.get_installed_version
        ):
            run_click_command(cci.version)
        assert (
            "You have the latest version of CumulusCI." in echo.call_args_list[-2][0][0]
        )

    @mock.patch("code.interact")
    def test_shell(self, interact):
        run_click_command(cci.shell)
        interact.assert_called_once()
        self.assertIn("config", interact.call_args[1]["local"])
        self.assertIn("runtime", interact.call_args[1]["local"])

    @mock.patch("runpy.run_path")
    def test_shell_script(self, runpy):
        run_click_command(cci.shell, script="foo.py")
        runpy.assert_called_once()
        self.assertIn("config", runpy.call_args[1]["init_globals"])
        self.assertIn("runtime", runpy.call_args[1]["init_globals"])
        assert runpy.call_args[0][0] == "foo.py", runpy.call_args[0]

    @mock.patch("builtins.print")
    def test_shell_code(self, print):
        run_click_command(cci.shell, python="print(config, runtime)")
        print.assert_called_once()

    @mock.patch("cumulusci.cli.cci.print")
    def test_shell_mutually_exclusive_args(self, print):
        with self.assertRaises(Exception) as e:
            run_click_command(
                cci.shell, script="foo.py", python="print(config, runtime)"
            )
        self.assertIn("Cannot specify both", str(e.exception))

    @mock.patch("code.interact")
    def test_shell__no_project(self, interact):
        with temporary_dir():
            run_click_command(cci.shell)
            interact.assert_called_once()

    def test_cover_command_groups(self):
        run_click_command(cci.project)
        run_click_command(cci.org)
        run_click_command(cci.task)
        run_click_command(cci.flow)
        run_click_command(cci.service)
        run_click_command(cci.service_connect)
        # no assertion; this test is for coverage of empty methods

    def test_validate_project_name(self):
        with self.assertRaises(click.UsageError):
            cci.validate_project_name("with spaces")

    def test_validate_project_name__valid(self):
        assert cci.validate_project_name("valid") == "valid"

    @mock.patch("cumulusci.cli.cci.click")
    def test_project_init(self, click):
        with temporary_dir():
            os.mkdir(".git")

            click.prompt.side_effect = (
                "testproj",  # project_name
                "testpkg",  # package_name
                "testns",  # package_namespace
                "43.0",  # api_version
                "mdapi",  # source_format
                "3",  # extend other URL
                "https://github.com/SalesforceFoundation/NPSP",  # github_url
                "default",  # git_default_branch
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
            run_click_command(cci.project_init, runtime=runtime)

            # Make sure expected files/dirs were created
            self.assertEqual(
                [
                    ".git/",
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
                ],
                recursive_list_files(),
            )

    @mock.patch("cumulusci.cli.cci.click")
    def test_project_init_tasks(self, click):
        """Verify that the generated cumulusci.yml file is readable and has the proper robot task"""
        with temporary_dir():
            os.mkdir(".git")

            click.prompt.side_effect = (
                "testproj",  # project_name
                "testpkg",  # package_name
                "testns",  # package_namespace
                "43.0",  # api_version
                "mdapi",  # source_format
                "3",  # extend other URL
                "https://github.com/SalesforceFoundation/NPSP",  # github_url
                "default",  # git_default_branch
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

            run_click_command(cci.project_init)

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
            self.assertDictEqual(config["tasks"], expected_tasks)

    def test_project_init_no_git(self):
        with temporary_dir():
            with self.assertRaises(click.ClickException):
                run_click_command(cci.project_init)

    def test_project_init_already_initted(self):
        with temporary_dir():
            os.mkdir(".git")
            with open("cumulusci.yml", "w"):
                pass  # create empty file

            with self.assertRaises(click.ClickException):
                run_click_command(cci.project_init)

    @mock.patch("click.echo")
    def test_project_info(self, echo):
        runtime = mock.Mock()
        runtime.project_config.project = {"test": "test"}

        run_click_command(cci.project_info, runtime=runtime)

        echo.assert_called_once_with("\x1b[1mtest:\x1b[0m test")

    def test_project_info__outside_project(self):
        runtime = mock.Mock()
        runtime.project_config = None
        runtime.project_config_error = NotInProject()
        with temporary_dir():
            with self.assertRaises(NotInProject):
                run_click_command(cci.project_info, runtime=runtime)

    def test_project_dependencies(self):
        out = []
        runtime = mock.Mock()
        runtime.project_config.pretty_dependencies.return_value = ["test:"]

        with mock.patch("click.echo", out.append):
            run_click_command(cci.project_dependencies, runtime=runtime)

        self.assertEqual("test:", "".join(out))

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_service_list(self, cli_tbl):
        runtime = mock.Mock()
        runtime.project_config.services = {
            "bad": {"description": "Unconfigured Service"},
            "test": {"description": "Test Service"},
        }
        runtime.keychain.list_services.return_value = ["test"]
        runtime.global_config.cli__plain_output = None

        run_click_command(
            cci.service_list, runtime=runtime, plain=False, print_json=False
        )

        cli_tbl.assert_called_with(
            [
                ["Name", "Description", "Configured"],
                ["bad", "Unconfigured Service", False],
                ["test", "Test Service", True],
            ],
            bool_cols=["Configured"],
            dim_rows=[1],
            title="Services",
            wrap_cols=["Description"],
        )

    @mock.patch("json.dumps")
    def test_service_list_json(self, json_):
        services = {
            "bad": {"description": "Unconfigured Service"},
            "test": {"description": "Test Service"},
        }
        runtime = mock.Mock()
        runtime.project_config.services = services
        runtime.keychain.list_services.return_value = ["test"]
        runtime.global_config.cli__plain_output = None

        run_click_command(
            cci.service_list, runtime=runtime, plain=False, print_json=True
        )

        json_.assert_called_with(services)

    def test_service_connect_list(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.Mock()
        runtime.project_config.services = {"test": {}}
        ctx = mock.Mock()

        with mock.patch("cumulusci.cli.cci.RUNTIME", runtime):
            result = multi_cmd.list_commands(ctx)
        self.assertEqual(["test"], result)

    def test_service_connect_list_global_keychain(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.Mock()
        runtime.project_config = None
        runtime.global_config.services = {"test": {}}
        ctx = mock.Mock()

        with mock.patch("cumulusci.cli.cci.RUNTIME", runtime):
            result = multi_cmd.list_commands(ctx)
        self.assertEqual(["test"], result)

    def test_service_connect(self):
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        runtime = mock.MagicMock()
        runtime.project_config.services = {
            "test": {"attributes": {"attr": {"required": False}}}
        }

        with mock.patch("cumulusci.cli.cci.RUNTIME", runtime):
            cmd = multi_cmd.get_command(ctx, "test")
            run_click_command(cmd, project=True)

        runtime.keychain.set_service.assert_called_once()

        run_click_command(cmd, project=False)

    def test_service_connect_global_keychain(self):
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        runtime = mock.MagicMock()
        runtime.project_config = None
        runtime.global_config.services = {
            "test": {"attributes": {"attr": {"required": False}}}
        }

        with mock.patch("cumulusci.cli.cci.RUNTIME", runtime):
            cmd = multi_cmd.get_command(ctx, "test")
            run_click_command(cmd, project=True)

        runtime.keychain.set_service.assert_called_once()

        run_click_command(cmd, project=False)

    def test_service_connect_invalid_service(self):
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        runtime = mock.MagicMock()
        runtime.project_config.services = {}

        with mock.patch("cumulusci.cli.cci.RUNTIME", runtime):
            with self.assertRaises(click.UsageError):
                multi_cmd.get_command(ctx, "test")

    def test_service_connect_validator(self):
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        runtime = mock.MagicMock()
        runtime.project_config.services = {
            "test": {
                "attributes": {},
                "validator": "cumulusci.cli.tests.test_cci.validate_service",
            }
        }

        with mock.patch("cumulusci.cli.cci.RUNTIME", runtime):
            cmd = multi_cmd.get_command(ctx, "test")
            with self.assertRaises(Exception) as cm:
                run_click_command(cmd, project=True)
            self.assertEqual("Validation failed", str(cm.exception))

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_service_info(self, cli_tbl):
        cli_tbl._table = mock.Mock()
        service_config = mock.Mock()
        service_config.config = {"description": "Test Service"}
        runtime = mock.Mock()
        runtime.keychain.get_service.return_value = service_config
        runtime.global_config.cli__plain_output = None

        run_click_command(
            cci.service_info, runtime=runtime, service_name="test", plain=False
        )

        cli_tbl.assert_called_with(
            [["Key", "Value"], ["\x1b[1mdescription\x1b[0m", "Test Service"]],
            title="test",
            wrap_cols=["Value"],
        )

    @mock.patch("click.echo")
    def test_service_info_not_configured(self, echo):
        runtime = mock.Mock()
        runtime.keychain.get_service.side_effect = ServiceNotConfigured

        run_click_command(
            cci.service_info, runtime=runtime, service_name="test", plain=False
        )

        self.assertIn("not configured for this project", echo.call_args[0][0])

    @mock.patch("webbrowser.open")
    def test_org_browser(self, browser_open):
        org_config = mock.Mock()
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        run_click_command(cci.org_browser, runtime=runtime, org_name="test")

        org_config.refresh_oauth_token.assert_called_once()
        browser_open.assert_called_once()
        runtime.keychain.set_org.assert_called_once_with(org_config)

    @mock.patch("cumulusci.cli.cci.CaptureSalesforceOAuth")
    @responses.activate
    def test_org_connect(self, oauth):
        oauth.return_value = mock.Mock(
            return_value={
                "instance_url": "https://instance",
                "access_token": "BOGUS",
                "id": "OODxxxxxxxxxxxx/user",
            }
        )
        runtime = mock.Mock()
        responses.add(
            method="GET",
            url="https://instance/services/oauth2/userinfo",
            body=b"{}",
            status=200,
        )
        responses.add(
            method="GET",
            url="https://instance/services/data/v45.0/sobjects/Organization/OODxxxxxxxxxxxx",
            json={
                "TrialExpirationDate": None,
                "OrganizationType": "Developer Edition",
                "IsSandbox": False,
            },
            status=200,
        )
        responses.add("GET", "https://instance/services/data", json=[{"version": 45.0}])
        run_click_command(
            cci.org_connect,
            runtime=runtime,
            org_name="test",
            sandbox=False,
            login_url="https://login.salesforce.com",
            default=True,
            global_org=False,
        )

        runtime.check_org_overwrite.assert_called_once()
        runtime.keychain.set_org.assert_called_once()
        org_config = runtime.keychain.set_org.call_args[0][0]
        assert org_config.expires == "Persistent"
        runtime.keychain.set_default_org.assert_called_once_with("test")

    @mock.patch("cumulusci.cli.cci.CaptureSalesforceOAuth")
    @responses.activate
    def test_org_connect_expires(self, oauth):
        oauth.return_value = mock.Mock(
            return_value={
                "instance_url": "https://instance",
                "access_token": "BOGUS",
                "id": "OODxxxxxxxxxxxx/user",
            }
        )
        runtime = mock.Mock()
        responses.add(
            method="GET",
            url="https://instance/services/oauth2/userinfo",
            body=b"{}",
            status=200,
        )
        responses.add(
            method="GET",
            url="https://instance/services/data/v45.0/sobjects/Organization/OODxxxxxxxxxxxx",
            json={
                "TrialExpirationDate": "1970-01-01T12:34:56.000+0000",
                "OrganizationType": "Developer Edition",
                "IsSandbox": True,
            },
            status=200,
        )
        responses.add("GET", "https://instance/services/data", json=[{"version": 45.0}])

        run_click_command(
            cci.org_connect,
            runtime=runtime,
            org_name="test",
            sandbox=True,
            login_url="https://test.salesforce.com",
            default=True,
            global_org=False,
        )

        runtime.check_org_overwrite.assert_called_once()
        runtime.keychain.set_org.assert_called_once()
        org_config = runtime.keychain.set_org.call_args[0][0]
        assert org_config.expires == date(1970, 1, 1)
        runtime.keychain.set_default_org.assert_called_once_with("test")

    def test_org_connect_connected_app_not_configured(self):
        runtime = mock.Mock()
        runtime.keychain.get_service.side_effect = ServiceNotConfigured

        with self.assertRaises(ServiceNotConfigured):
            run_click_command(
                cci.org_connect,
                runtime=runtime,
                org_name="test",
                sandbox=True,
                login_url="https://login.salesforce.com",
                default=True,
                global_org=False,
            )

    def test_org_default(self):
        runtime = mock.Mock()

        run_click_command(
            cci.org_default, runtime=runtime, org_name="test", unset=False
        )

        runtime.keychain.set_default_org.assert_called_once_with("test")

    def test_org_default_unset(self):
        runtime = mock.Mock()

        run_click_command(cci.org_default, runtime=runtime, org_name="test", unset=True)

        runtime.keychain.unset_default_org.assert_called_once()

    @mock.patch("sarge.Command")
    def test_org_import(self, cmd):
        runtime = mock.Mock()
        result = b"""{
            "result": {
                "createdDate": "1970-01-01T00:00:00.000Z",
                "expirationDate": "1970-01-01",
                "instanceUrl": "url",
                "accessToken": "access!token",
                "username": "test@test.org",
                "password": "password"
            }
        }"""
        cmd.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(result), returncode=0
        )

        out = []
        with mock.patch("click.echo", out.append):
            run_click_command(
                cci.org_import,
                username_or_alias="test@test.org",
                org_name="test",
                runtime=runtime,
            )
            runtime.keychain.set_org.assert_called_once()
        self.assertTrue(
            "Imported scratch org: access, username: test@test.org" in "".join(out)
        )

    def test_calculate_org_days(self):
        info_1 = {
            "created_date": "1970-01-01T12:34:56.789Z",
            "expiration_date": "1970-01-02",
        }
        actual_days = cci.calculate_org_days(info_1)
        assert 1 == actual_days

        info_7 = {
            "created_date": "1970-01-01T12:34:56.789+0000",
            "expiration_date": "1970-01-08",
        }
        actual_days = cci.calculate_org_days(info_7)
        assert 7 == actual_days

        info_14 = {
            "created_date": "1970-01-01T12:34:56.000+0000",
            "expiration_date": "1970-01-15",
        }
        actual_days = cci.calculate_org_days(info_14)
        assert 14 == actual_days

        info_bad__no_created_date = {"expiration_date": "1970-01-15"}
        actual_days = cci.calculate_org_days(info_bad__no_created_date)
        assert 1 == actual_days

        info_bad__no_expiration_date = {"created_date": "1970-01-01T12:34:56.000+0000"}
        actual_days = cci.calculate_org_days(info_bad__no_expiration_date)
        assert 1 == actual_days

    def test_org_info(self):
        org_config = mock.Mock()
        org_config.config = {"days": 1, "default": True, "password": None}
        org_config.expires = date.today()
        org_config.latest_api_version = "42.0"
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        with mock.patch("cumulusci.cli.cci.CliTable") as cli_tbl:
            run_click_command(
                cci.org_info, runtime=runtime, org_name="test", print_json=False
            )
            cli_tbl.assert_called_with(
                [
                    ["Key", "Value"],
                    ["\x1b[1mapi_version\x1b[0m", "42.0"],
                    ["\x1b[1mdays\x1b[0m", "1"],
                    ["\x1b[1mdefault\x1b[0m", "True"],
                    ["\x1b[1mpassword\x1b[0m", "None"],
                ],
                wrap_cols=["Value"],
            )

        runtime.keychain.set_org.assert_called_once_with(org_config)

    def test_org_info_json(self):
        class Unserializable(object):
            def __str__(self):
                return "<unserializable>"

        org_config = mock.Mock()
        org_config.config = {"test": "test", "unserializable": Unserializable()}
        org_config.expires = date.today()
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        out = []
        with mock.patch("click.echo", out.append):
            run_click_command(
                cci.org_info, runtime=runtime, org_name="test", print_json=True
            )

        org_config.refresh_oauth_token.assert_called_once()
        self.assertEqual(
            '{\n    "test": "test",\n    "unserializable": "<unserializable>"\n}',
            "".join(out),
        )
        runtime.keychain.set_org.assert_called_once_with(org_config)

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_org_list(self, cli_tbl):
        runtime = mock.Mock()
        runtime.global_config.cli__plain_output = None
        runtime.keychain.list_orgs.return_value = [
            "test0",
            "test1",
            "test2",
            "test3",
            "test4",
            "test5",
            "test6",
        ]
        runtime.keychain.get_org.side_effect = [
            ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "test0",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now(),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test1@example.com",
                    "instance_url": "https://sneaky-master-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test1",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "Persistent",
                    "expired": False,
                    "config_name": "dev",
                    "username": "test2@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test2",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "2019-11-19",
                    "expired": False,
                    "config_name": "dev",
                    "username": "test3@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test3",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expired": False,
                    "config_name": "dev",
                    "username": "test4@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test4",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "expires": "2019-11-19",
                    "expired": False,
                    "config_name": "dev",
                    "username": "test5@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test5",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "expired": False,
                    "config_name": "dev",
                    "username": "test6@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test6",
            ),
        ]

        run_click_command(cci.org_list, runtime=runtime, plain=False)

        scratch_table_call = mock.call(
            [
                ["Name", "Default", "Days", "Expired", "Config", "Domain"],
                ["test0", True, "7", True, "dev", ""],
                ["test1", False, "1/7", False, "dev", "sneaky-master-2330-dev-ed.cs22"],
            ],
            bool_cols=["Default"],
            title="Scratch Orgs",
            dim_rows=[0, 1],
        )
        connected_table_call = mock.call(
            [
                ["Name", "Default", "Username", "Expires"],
                ["test2", False, "test2@example.com", "Persistent"],
                ["test3", False, "test3@example.com", "2019-11-19"],
                ["test4", False, "test4@example.com", "Unknown"],
                ["test5", False, "test5@example.com", "2019-11-19"],
                ["test6", False, "test6@example.com", "Unknown"],
            ],
            bool_cols=["Default"],
            title="Connected Orgs",
            wrap_cols=["Username"],
        )

        self.assertIn(scratch_table_call, cli_tbl.call_args_list)
        self.assertIn(connected_table_call, cli_tbl.call_args_list)

    @mock.patch("click.echo")
    def test_org_prune(self, echo):
        runtime = mock.Mock()
        runtime.keychain.list_orgs.return_value = [
            "shape1",
            "shape2",
            "remove1",
            "remove2",
            "active1",
            "active2",
            "persistent",
        ]
        runtime.project_config.orgs__scratch = {
            "shape1": True,
            "shape2": True,
        }

        runtime.keychain.get_org.side_effect = [
            ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "shape1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now(),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test1@example.com",
                },
                "shape2",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime(1999, 11, 1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "remove1@example.com",
                },
                "remove1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime(1999, 11, 1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "remove2@example.com",
                },
                "remove2",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active1@example.com",
                },
                "active1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active2@example.com",
                },
                "active2",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "Persistent",
                    "expired": False,
                    "config_name": "dev",
                    "username": "persistent@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "persistent",
            ),
        ]

        run_click_command(cci.org_prune, runtime=runtime, include_active=False)

        echo.assert_any_call(
            "Successfully removed 2 expired scratch orgs: remove1, remove2"
        )
        echo.assert_any_call("Skipped org shapes: shape1, shape2")
        echo.assert_any_call("Skipped active orgs: active1, active2")

        runtime.keychain.remove_org.assert_has_calls(
            [mock.call("remove1"), mock.call("remove2")]
        )
        assert runtime.keychain.remove_org.call_count == 2

    @mock.patch("click.echo")
    def test_org_prune_no_expired(self, echo):
        runtime = mock.Mock()
        runtime.keychain.list_orgs.return_value = [
            "shape1",
            "shape2",
            "active1",
            "active2",
            "persistent",
        ]
        runtime.project_config.orgs__scratch = {
            "shape1": True,
            "shape2": True,
        }

        runtime.keychain.get_org.side_effect = [
            ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "shape1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now(),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test1@example.com",
                },
                "shape2",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active1@example.com",
                },
                "active1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active2@example.com",
                },
                "active2",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "Persistent",
                    "expired": False,
                    "config_name": "dev",
                    "username": "persistent@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "persistent",
            ),
        ]

        run_click_command(cci.org_prune, runtime=runtime, include_active=False)
        runtime.keychain.remove_org.assert_not_called()

        echo.assert_any_call("No expired scratch orgs to delete. ✨")

    @mock.patch("click.echo")
    def test_org_prune_include_active(self, echo):
        runtime = mock.Mock()
        runtime.keychain.list_orgs.return_value = [
            "shape1",
            "shape2",
            "remove1",
            "remove2",
            "active1",
            "active2",
            "persistent",
        ]
        runtime.project_config.orgs__scratch = {
            "shape1": True,
            "shape2": True,
        }

        runtime.keychain.get_org.side_effect = [
            ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "shape1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "days": 7,
                    "config_name": "dev",
                    "username": "test1@example.com",
                },
                "shape2",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime(1999, 11, 1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "remove1@example.com",
                },
                "remove1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime(1999, 11, 1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "remove2@example.com",
                },
                "remove2",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active1@example.com",
                },
                "active1",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=1),
                    "days": 7,
                    "config_name": "dev",
                    "username": "active2@example.com",
                },
                "active2",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expires": "Persistent",
                    "expired": False,
                    "config_name": "dev",
                    "username": "persistent@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "persistent",
            ),
        ]

        run_click_command(cci.org_prune, runtime=runtime, include_active=True)

        echo.assert_any_call(
            "Successfully removed 2 expired scratch orgs: remove1, remove2"
        )
        echo.assert_any_call(
            "Successfully removed 2 active scratch orgs: active1, active2"
        )
        echo.assert_any_call("Skipped org shapes: shape1, shape2")

        runtime.keychain.remove_org.assert_has_calls(
            [
                mock.call("remove1"),
                mock.call("remove2"),
                mock.call("active1"),
                mock.call("active2"),
            ]
        )
        assert runtime.keychain.remove_org.call_count == 4

    def test_org_remove(self):
        org_config = mock.Mock()
        org_config.can_delete.return_value = True
        runtime = mock.Mock()
        runtime.keychain.get_org.return_value = org_config

        run_click_command(
            cci.org_remove, runtime=runtime, org_name="test", global_org=False
        )

        org_config.delete_org.assert_called_once()
        runtime.keychain.remove_org.assert_called_once_with("test", False)

    @mock.patch("click.echo")
    def test_org_remove_delete_error(self, echo):
        org_config = mock.Mock()
        org_config.can_delete.return_value = True
        org_config.delete_org.side_effect = Exception
        runtime = mock.Mock()
        runtime.keychain.get_org.return_value = org_config

        run_click_command(
            cci.org_remove, runtime=runtime, org_name="test", global_org=False
        )

        echo.assert_any_call("Deleting scratch org failed with error:")

    def test_org_remove_not_found(self):
        runtime = mock.Mock()
        runtime.keychain.get_org.side_effect = OrgNotFound

        with self.assertRaises(click.ClickException) as cm:
            run_click_command(
                cci.org_remove, runtime=runtime, org_name="test", global_org=False
            )

        self.assertEqual("Org test does not exist in the keychain", str(cm.exception))

    def test_org_scratch(self):
        runtime = mock.Mock()
        runtime.project_config.orgs__scratch = {"dev": {"orgName": "Dev"}}

        run_click_command(
            cci.org_scratch,
            runtime=runtime,
            config_name="dev",
            org_name="test",
            default=True,
            devhub="hub",
            days=7,
            no_password=True,
        )

        runtime.check_org_overwrite.assert_called_once()
        runtime.keychain.create_scratch_org.assert_called_with(
            "test", "dev", 7, set_password=False
        )
        runtime.keychain.set_default_org.assert_called_with("test")

    def test_org_scratch__not_default(self):
        runtime = mock.Mock()
        runtime.project_config.orgs__scratch = {"dev": {"orgName": "Dev"}}

        run_click_command(
            cci.org_scratch,
            runtime=runtime,
            config_name="dev",
            org_name="test",
            default=False,
            devhub="hub",
            days=7,
            no_password=True,
        )

        runtime.check_org_overwrite.assert_called_once()
        runtime.keychain.create_scratch_org.assert_called_with(
            "test", "dev", 7, set_password=False
        )

    def test_org_scratch_no_configs(self):
        runtime = mock.Mock()
        runtime.project_config.orgs__scratch = None

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.org_scratch,
                runtime=runtime,
                config_name="dev",
                org_name="test",
                default=True,
                devhub="hub",
                days=7,
                no_password=True,
            )

    def test_org_scratch_config_not_found(self):
        runtime = mock.Mock()
        runtime.project_config.orgs__scratch = {"bogus": {}}

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.org_scratch,
                runtime=runtime,
                config_name="dev",
                org_name="test",
                default=True,
                devhub="hub",
                days=7,
                no_password=True,
            )

    def test_org_scratch_delete(self):
        org_config = mock.Mock()
        runtime = mock.Mock()
        runtime.keychain.get_org.return_value = org_config

        run_click_command(cci.org_scratch_delete, runtime=runtime, org_name="test")

        org_config.delete_org.assert_called_once()
        runtime.keychain.set_org.assert_called_once_with(org_config)

    def test_org_scratch_delete_not_scratch(self):
        org_config = mock.Mock(scratch=False)
        runtime = mock.Mock()
        runtime.keychain.get_org.return_value = org_config

        with self.assertRaises(click.UsageError):
            run_click_command(cci.org_scratch_delete, runtime=runtime, org_name="test")

    def test_org_scratch_delete_error(self):
        org_config = mock.Mock()
        org_config.delete_org.side_effect = ScratchOrgException
        runtime = mock.Mock()
        runtime.keychain.get_org.return_value = org_config

        with self.assertRaises(ScratchOrgException):
            run_click_command(cci.org_scratch_delete, runtime=runtime, org_name="test")

    @mock.patch("cumulusci.cli.cci.get_simple_salesforce_connection")
    @mock.patch("code.interact")
    def test_org_shell(self, mock_code, mock_sf):
        org_config = mock.Mock()
        org_config.instance_url = "https://salesforce.com"
        org_config.access_token = "TEST"
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        run_click_command(cci.org_shell, runtime=runtime, org_name="test")

        org_config.refresh_oauth_token.assert_called_once()
        mock_sf.assert_called_once_with(runtime.project_config, org_config)
        runtime.keychain.set_org.assert_called_once_with(org_config)

        mock_code.assert_called_once()
        self.assertIn("sf", mock_code.call_args[1]["local"])

    @mock.patch("runpy.run_path")
    def test_org_shell_script(self, runpy):
        org_config = mock.Mock()
        org_config.instance_url = "https://salesforce.com"
        org_config.access_token = "TEST"
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)
        run_click_command(
            cci.org_shell, runtime=runtime, org_name="test", script="foo.py"
        )
        runpy.assert_called_once()
        self.assertIn("sf", runpy.call_args[1]["init_globals"])
        assert runpy.call_args[0][0] == "foo.py", runpy.call_args[0]

    @mock.patch("cumulusci.cli.ui.SimpleSalesforceUIHelpers.describe")
    def test_org_shell_describe(self, describe):
        org_config = mock.Mock()
        org_config.instance_url = "https://salesforce.com"
        org_config.access_token = "TEST"
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)
        run_click_command(
            cci.org_shell, runtime=runtime, org_name="test", python="describe('blah')"
        )
        describe.assert_called_once()
        assert "blah" in describe.call_args[0][0]

    @mock.patch("cumulusci.cli.cci.print")
    def test_org_shell_mutually_exclusive_args(self, print):
        org_config = mock.Mock()
        org_config.instance_url = "https://salesforce.com"
        org_config.access_token = "TEST"
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)
        with self.assertRaises(Exception) as e:
            run_click_command(
                cci.org_shell,
                runtime=runtime,
                org_name="foo",
                script="foo.py",
                python="print(config, runtime)",
            )
        self.assertIn("Cannot specify both", str(e.exception))

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_task_list(self, cli_tbl):
        runtime = mock.Mock()
        runtime.global_config.cli__plain_output = None
        runtime.project_config.list_tasks.return_value = [
            {"name": "test_task", "description": "Test Task", "group": "Test Group"}
        ]

        run_click_command(cci.task_list, runtime=runtime, plain=False, print_json=False)

        cli_tbl.assert_called_with(
            [["Task", "Description"], ["test_task", "Test Task"]],
            "Test Group",
            wrap_cols=["Description"],
        )

    @mock.patch("json.dumps")
    def test_task_list_json(self, json_):
        task_dicts = {
            "name": "test_task",
            "description": "Test Task",
            "group": "Test Group",
        }
        runtime = mock.Mock()
        runtime.global_config.cli__plain_output = None
        runtime.project_config.list_tasks.return_value = [task_dicts]

        run_click_command(cci.task_list, runtime=runtime, plain=False, print_json=True)

        json_.assert_called_with([task_dicts])

    @mock.patch("cumulusci.cli.cci.doc_task")
    def test_task_doc(self, doc_task):
        runtime = mock.Mock()
        runtime.global_config.tasks = {"test": {}}

        run_click_command(cci.task_doc, runtime=runtime)
        doc_task.assert_called()

    @mock.patch("cumulusci.cli.cci.rst2ansi")
    @mock.patch("cumulusci.cli.cci.doc_task")
    def test_task_info(self, doc_task, rst2ansi):
        runtime = mock.Mock()
        runtime.project_config.tasks__test = {"options": {}}

        run_click_command(cci.task_info, runtime=runtime, task_name="test")

        doc_task.assert_called_once()
        rst2ansi.assert_called_once()

    def test_task_run(self):
        runtime = mock.Mock()
        runtime.get_org.return_value = (None, None)
        runtime.project_config = BaseProjectConfig(
            None,
            config={
                "tasks": {
                    "test": {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
                }
            },
        )
        DummyTask._run_task = mock.Mock()

        run_click_command(
            cci.task_run,
            runtime=runtime,
            task_name="test",
            org=None,
            o=[("color", "blue")],
            debug=False,
            debug_before=False,
            debug_after=False,
            no_prompt=True,
        )

        DummyTask._run_task.assert_called_once()

    def test_task_run_invalid_option(self):
        runtime = mock.Mock()
        runtime.get_org.return_value = (None, None)
        runtime.project_config.get_task.return_value = TaskConfig(
            {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
        )

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.task_run,
                runtime=runtime,
                task_name="test",
                org=None,
                o=[("bogus", "blue")],
                debug=False,
                debug_before=False,
                debug_after=False,
                no_prompt=True,
            )

    @mock.patch("pdb.set_trace")
    def test_task_run_debug_before(self, set_trace):
        runtime = mock.Mock()
        runtime.get_org.return_value = (None, None)
        runtime.project_config = BaseProjectConfig(
            None,
            config={
                "tasks": {
                    "test": {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
                }
            },
        )
        set_trace.side_effect = SetTrace

        with self.assertRaises(SetTrace):
            run_click_command(
                cci.task_run,
                runtime=runtime,
                task_name="test",
                org=None,
                o=[("color", "blue")],
                debug=False,
                debug_before=True,
                debug_after=False,
                no_prompt=True,
            )

    @mock.patch("pdb.set_trace")
    def test_task_run_debug_after(self, set_trace):
        runtime = mock.Mock()
        runtime.get_org.return_value = (None, None)
        runtime.project_config = BaseProjectConfig(
            None,
            config={
                "tasks": {
                    "test": {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
                }
            },
        )
        set_trace.side_effect = SetTrace

        with self.assertRaises(SetTrace):
            run_click_command(
                cci.task_run,
                runtime=runtime,
                task_name="test",
                org=None,
                o=[("color", "blue")],
                debug=False,
                debug_before=False,
                debug_after=True,
                no_prompt=True,
            )

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_flow_list(self, cli_tbl):
        runtime = mock.Mock()
        runtime.project_config.list_flows.return_value = [
            {"name": "test_flow", "description": "Test Flow"}
        ]
        runtime.global_config.cli__plain_output = None
        run_click_command(cci.flow_list, runtime=runtime, plain=False, print_json=False)

        cli_tbl.assert_called_with(
            [["Name", "Description"], ["test_flow", "Test Flow"]],
            title="Flows",
            wrap_cols=["Description"],
        )

    @mock.patch("json.dumps")
    def test_flow_list_json(self, json_):
        flows = [{"name": "test_flow", "description": "Test Flow"}]
        runtime = mock.Mock()
        runtime.project_config.list_flows.return_value = flows
        runtime.global_config.cli__plain_output = None

        run_click_command(cci.flow_list, runtime=runtime, plain=False, print_json=True)

        json_.assert_called_with(flows)

    @mock.patch("click.echo")
    def test_flow_info(self, echo):
        runtime = mock.Mock()
        flow_config = FlowConfig({"description": "Test Flow", "steps": {}})
        runtime.get_flow.return_value = FlowCoordinator(None, flow_config)

        run_click_command(cci.flow_info, runtime=runtime, flow_name="test")

        echo.assert_called_with("Description: Test Flow")

    def test_flow_info__not_found(self):
        runtime = mock.Mock()
        runtime.get_flow.side_effect = FlowNotFoundError
        with self.assertRaises(click.UsageError):
            run_click_command(cci.flow_info, runtime=runtime, flow_name="test")

    def test_flow_run(self):
        org_config = mock.Mock(scratch=True, config={})
        runtime = CliRuntime(
            config={
                "flows": {"test": {"steps": {1: {"task": "test_task"}}}},
                "tasks": {
                    "test_task": {
                        "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
                        "description": "Test Task",
                    }
                },
            },
            load_keychain=False,
        )
        runtime.get_org = mock.Mock(return_value=("test", org_config))
        runtime.get_flow = mock.Mock()

        run_click_command(
            cci.flow_run,
            runtime=runtime,
            flow_name="test",
            org="test",
            delete_org=True,
            debug=False,
            o=[("test_task__color", "blue")],
            skip=(),
            no_prompt=True,
        )

        runtime.get_flow.assert_called_once_with(
            "test", options={"test_task": {"color": "blue"}}
        )
        org_config.delete_org.assert_called_once()

    def test_flow_run_delete_non_scratch(self,):
        org_config = mock.Mock(scratch=False)
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.flow_run,
                runtime=runtime,
                flow_name="test",
                org="test",
                delete_org=True,
                debug=False,
                o=None,
                skip=(),
                no_prompt=True,
            )

    @mock.patch("click.echo")
    def test_flow_run_org_delete_error(self, echo):
        org_config = mock.Mock(scratch=True, config={})
        org_config.delete_org.side_effect = Exception
        runtime = CliRuntime(
            config={
                "flows": {"test": {"steps": {1: {"task": "test_task"}}}},
                "tasks": {
                    "test_task": {
                        "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
                        "description": "Test Task",
                    }
                },
            },
            load_keychain=False,
        )
        runtime.get_org = mock.Mock(return_value=("test", org_config))
        DummyTask._run_task = mock.Mock()

        run_click_command(
            cci.flow_run,
            runtime=runtime,
            flow_name="test",
            org="test",
            delete_org=True,
            debug=False,
            o=None,
            skip=(),
            no_prompt=True,
        )

        echo.assert_any_call(
            "Scratch org deletion failed.  Ignoring the error below to complete the flow:"
        )

    @mock.patch("cumulusci.cli.cci.click.echo")
    @mock.patch("cumulusci.cli.cci.CCI_LOGFILE_PATH")
    def test_error_info_no_logfile_present(self, log_path, echo):
        log_path.is_file.return_value = False
        run_click_command(cci.error_info, max_lines=30)

        echo.assert_called_once_with(f"No logfile found at: {cci.CCI_LOGFILE_PATH}")

    @mock.patch("cumulusci.cli.cci.click.echo")
    @mock.patch("cumulusci.cli.cci.CCI_LOGFILE_PATH")
    def test_error_info(self, log_path, echo):
        log_path.is_file.return_value = True
        log_path.read_text.return_value = (
            "This\nis\na\ntest\nTraceback (most recent call last):\n1\n2\n3\n4"
        )

        run_click_command(cci.error_info, max_lines=30)
        echo.assert_called_once_with("\nTraceback (most recent call last):\n1\n2\n3\n4")

    @mock.patch("cumulusci.cli.cci.click.echo")
    @mock.patch("cumulusci.cli.cci.CCI_LOGFILE_PATH")
    def test_error_info_output_less(self, log_path, echo):
        log_path.is_file.return_value = True
        log_path.read_text.return_value = (
            "This\nis\na\ntest\nTraceback (most recent call last):\n1\n2\n3\n4"
        )

        run_click_command(cci.error_info, max_lines=3)
        echo.assert_called_once_with("\n1\n2\n3\n4")

    def test_lines_from_traceback_no_traceback(self):
        output = cci.lines_from_traceback("test_content", 10)
        assert "\nNo stacktrace found in:" in output

    def test_lines_from_traceback(self):
        traceback = "\nTraceback (most recent call last):\n1\n2\n3\n4"
        content = "This\nis\na" + traceback
        output = cci.lines_from_traceback(content, 10)
        assert output == traceback


class SetTrace(Exception):
    pass


class DummyTask(BaseTask):
    task_options = {"color": {}}


def validate_service(options):
    raise Exception("Validation failed")

import re
from pathlib import Path
from unittest import mock

import github3
import pytest

import cumulusci
from cumulusci.cli.error import get_traceback
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.utils import temporary_dir

from .. import error
from .utils import run_click_command


class TestErrorCommands:
    @mock.patch("click.echo")
    @mock.patch("cumulusci.cli.error.CCI_LOGFILE_PATH")
    def test_error_info_no_logfile_present(self, log_path, echo):
        log_path.is_file.return_value = False
        run_click_command(error.error_info)

        echo.assert_called_once_with(f"No logfile found at: {error.CCI_LOGFILE_PATH}")

    @mock.patch("click.echo")
    def test_error_info(self, echo):
        with temporary_dir() as path:
            logfile = Path(path) / "cci.log"
            logfile.write_text(
                "This\nis\na\ntest\nTraceback (most recent call last):\n1\n2\n3\n\u2603",
                encoding="utf-8",
            )
            with mock.patch("cumulusci.cli.error.CCI_LOGFILE_PATH", logfile):
                run_click_command(error.error_info)
        echo.assert_called_once_with(
            "\nTraceback (most recent call last):\n1\n2\n3\n\u2603"
        )

    def test_get_traceback__no_traceback(self):
        output = get_traceback("test_content")
        assert "\nNo stacktrace found in:" in output

    def test_get_traceback(self):
        traceback = "\nTraceback (most recent call last):\n1\n2\n3\n4"
        content = "This\nis\na" + traceback
        output = get_traceback(content)
        assert output == traceback

    @mock.patch("cumulusci.cli.error.CCI_LOGFILE_PATH")
    @mock.patch("webbrowser.open")
    @mock.patch("cumulusci.cli.error.platform")
    @mock.patch("cumulusci.cli.error.sys")
    @mock.patch("cumulusci.cli.error.datetime")
    @mock.patch("cumulusci.cli.error.create_gist")
    @mock.patch("cumulusci.cli.error.get_github_api")
    def test_error_gist(
        self, gh_api, create_gist, date, sys, platform, webbrowser_open, logfile_path
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
            "token": "token",
        }

        run_click_command(error.gist, runtime=runtime)

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
        webbrowser_open.assert_called_once_with(expected_gist_url)

    @mock.patch("cumulusci.cli.error.CCI_LOGFILE_PATH")
    @mock.patch("cumulusci.cli.error.click")
    @mock.patch("cumulusci.cli.error.platform")
    @mock.patch("cumulusci.cli.error.sys")
    @mock.patch("cumulusci.cli.error.datetime")
    @mock.patch("cumulusci.cli.error.create_gist")
    @mock.patch("cumulusci.cli.error.get_github_api")
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
            "token": "token",
        }

        with pytest.raises(
            CumulusCIException, match="An error occurred attempting to create your gist"
        ):
            run_click_command(error.gist, runtime=runtime)

        class GitHubExceptionWithResponse(github3.exceptions.NotFoundError, mock.Mock):
            def __init__(self, status_code):
                self.response = mock.Mock(
                    status_code=status_code,
                    headers={},
                    url="https://api.github.com/gists",
                )

        create_gist.side_effect = GitHubExceptionWithResponse(404)
        with pytest.raises(CumulusCIException, match=re.escape(error.GIST_404_ERR_MSG)):
            run_click_command(error.gist, runtime=runtime)

    @mock.patch("cumulusci.cli.error.CCI_LOGFILE_PATH")
    @mock.patch("cumulusci.cli.error.click")
    @mock.patch("cumulusci.cli.error.datetime")
    @mock.patch("cumulusci.cli.error.create_gist")
    @mock.patch("cumulusci.cli.error.get_github_api")
    def test_gist__file_not_found(self, gh_api, create_gist, date, click, logfile_path):
        logfile_path.is_file.return_value = False
        with pytest.raises(CumulusCIException):
            run_click_command(error.gist)

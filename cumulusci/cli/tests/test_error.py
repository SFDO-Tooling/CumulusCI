import re
import sys
from unittest import mock

import github3
import pytest

import cumulusci
from cumulusci.cli.error import get_context_info, get_traceback
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.runtime import BaseCumulusCI

from .. import error
from .utils import run_cli_command


class TestErrorCommands:
    def test_error_info(self, capsys):
        logfile = error.get_logfile_path()
        logfile.parent.mkdir(parents=True)
        logfile.write_text(
            "This\nis\na\ntest\nTraceback (most recent call last):\n1\n2\n3\n\u2603",
            encoding="utf-8",
        )
        result = run_cli_command("error", "info")

        assert "\nTraceback (most recent call last):\n1\n2\n3\n\u2603" in result.stdout

    @mock.patch("cumulusci.cli.error.warn_if_no_long_paths")
    def test_error_info_win_warn(self, warn_if):
        logfile = error.get_logfile_path()
        logfile.parent.mkdir(parents=True)
        logfile.write_text(
            "This\nis\na\ntest\nTraceback (most recent call last):\n1\n2\n3\n\u2603",
            encoding="utf-8",
        )
        run_cli_command("error", "info")

        warn_if.assert_called_once()

    def test_error_info__no_logfile_present(self, capsys):
        result = run_cli_command("error", "info")
        assert f"No logfile found at: {error.get_logfile_path()}" in result.stdout

    def test_get_traceback__no_traceback(self):
        output = get_traceback("test_content")
        assert "\nNo stacktrace found in:" in output

    def test_get_traceback(self):
        traceback = "\nTraceback (most recent call last):\n1\n2\n3\n4"
        content = "This\nis\na" + traceback
        output = get_traceback(content)
        assert output == traceback

    @mock.patch("webbrowser.open")
    @mock.patch("cumulusci.cli.error.platform")
    @mock.patch("cumulusci.cli.error.sys")
    @mock.patch("cumulusci.cli.error.datetime")
    @mock.patch("cumulusci.cli.error.create_gist")
    @mock.patch("cumulusci.cli.error.get_github_api")
    def test_error_gist(
        self, gh_api, create_gist, date, sys, platform, webbrowser_open
    ):

        platform.uname.return_value = mock.Mock(system="Rossian", machine="x68_46")
        sys.version = "1.0.0 (default Jul 24 2019)"
        sys.executable = "User/bob.ross/.pyenv/versions/cci-374/bin/python"
        date.utcnow.return_value = "01/01/1970"
        gh_api.return_value = mock.Mock()
        expected_gist_url = "https://gist.github.com/1234567890abcdefghijkl"
        create_gist.return_value = mock.Mock(html_url=expected_gist_url)

        logfile_path = error.get_logfile_path()
        logfile_path.parent.mkdir(parents=True)
        expected_logfile_content = "Hello there, I'm a logfile."
        logfile_path.write_text(expected_logfile_content)

        runtime = mock.Mock()
        runtime.project_config.repo_root = None
        runtime.keychain.get_service.return_value.config = {
            "username": "usrnm",
            "token": "token",
        }

        run_cli_command("error", "gist", runtime=runtime)

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

    @pytest.mark.skipif(
        sys.version_info > (3, 11), reason="requires python3.10 or higher"
    )
    @mock.patch("cumulusci.cli.error.platform")
    @mock.patch("cumulusci.cli.error.sys")
    @mock.patch("cumulusci.cli.error.datetime")
    @mock.patch("cumulusci.cli.error.create_gist")
    @mock.patch("cumulusci.cli.error.get_github_api")
    def test_gist__creation_error(self, gh_api, create_gist, date, sys, platform):
        logfile_path = error.get_logfile_path()
        logfile_path.parent.mkdir(parents=True)
        expected_logfile_content = "Hello there, I'm a logfile."
        logfile_path.write_text(expected_logfile_content)

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
            run_cli_command("error", "gist", runtime=runtime)

        class GitHubExceptionWithResponse(github3.exceptions.NotFoundError, mock.Mock):
            def __init__(self, status_code):
                self.response = mock.Mock(
                    status_code=status_code,
                    headers={},
                    url="https://api.github.com/gists",
                )

        create_gist.side_effect = GitHubExceptionWithResponse(404)
        with pytest.raises(CumulusCIException, match=re.escape(error.GIST_404_ERR_MSG)):
            run_cli_command("error", "gist", runtime=runtime)

    def test_gist__file_not_found(self):
        runtime = BaseCumulusCI()
        with pytest.raises(CumulusCIException, match="No logfile to open"):
            run_cli_command("error", "gist", runtime=runtime)

    @pytest.mark.skipif(
        sys.platform.startswith("win"), reason="Requires Windows Registry"
    )
    @mock.patch("cumulusci.cli.error.win32_long_paths_enabled")
    def test_get_context_not_win(self, win32_check):
        info = get_context_info()
        win32_check.assert_not_called()
        assert "Windows" not in info

    @pytest.mark.skipif(
        not sys.platform.startswith("win"), reason="Requires Windows Registry"
    )
    @mock.patch("cumulusci.cli.error.win32_long_paths_enabled")
    def test_get_context_win(self, win32_check):
        info = get_context_info()
        win32_check.assert_called_once()
        assert "Windows" in info

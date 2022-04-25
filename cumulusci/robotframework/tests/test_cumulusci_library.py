import logging
from pathlib import Path
from unittest import mock

import pytest
import robot.api.logger

from cumulusci.core.config import BaseProjectConfig, UniversalConfig
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.core.tests.utils import MockLoggerMixin
from cumulusci.robotframework.CumulusCI import CumulusCI
from cumulusci.tests.util import DummyKeychain, DummyOrgConfig
from cumulusci.utils import temporary_dir


class TestCumulusCILibrary(MockLoggerMixin):
    def setup_method(self):
        self.universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config,
            {
                "project": {"name": "Test"},
                "tasks": {
                    "get_pwd": {
                        "class_path": "cumulusci.tasks.command.Command",
                        "options": {
                            "command": "pwd",
                        },
                    },
                },
                "sources": {
                    "example": {"path": "/tmp"},
                },
            },
            repo_info={"root": Path(__file__).parent.absolute()},
        )
        self.project_config.set_keychain(DummyKeychain())

        self.cumulusci = CumulusCI()
        self.cumulusci._project_config = self.project_config
        self.cumulusci._org = mock.Mock()
        self.cumulusci._org.name = "mock org"
        self.cumulusci._org.instance_url = "https://test.example.com"

        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages

    def test_run_task(self):
        """Smoke test; can we run the command task?"""
        result = self.cumulusci.run_task("get_pwd")
        assert result["returncode"] == 0

    def test_run_task_robot_logger(self):
        """Verify that 'run task' uses the robot logger"""
        with mock.patch.object(self.cumulusci, "_run_task"):
            self.cumulusci.run_task("get_pwd")
            args, kwargs = self.cumulusci._run_task.call_args
            task = args[0]
            assert task.logger == robot.api.logger

    def test_robot_logger_supports_warning(self):
        """Verify that 'run task' uses a logger that supports .warning()

        Python deprecated the logger method "warn" in favor of
        "warning". Robot didn't get the memo and has "warn" instead of
        "warning".  Since our tasks use "warning", this verifies that
        we've patched the robot logger before passing it to the task
        constructor.

        """
        with mock.patch.object(self.cumulusci, "_run_task"):
            self.cumulusci.run_task("get_pwd")
            args, kwargs = self.cumulusci._run_task.call_args
            task = args[0]
            assert hasattr(
                task.logger, "warning"
            ), "robot logger should have a warning method but doesn't"

    def test_robot_logger_supports_log(self):
        """Verify that 'run task' uses a logger that supports .log()

        log() normally will be passed a predefined log level (eg:
        logging.INFO, logging.DEBUG, etc), but it can take any integer
        which get mapped to a robot log level as a string. This attempts
        to catch all of the various mappings.
        """
        with mock.patch.object(self.cumulusci, "_run_task"):
            self.cumulusci.run_task("get_pwd")
            args, kwargs = self.cumulusci._run_task.call_args
            task = args[0]
            with mock.patch.object(task.logger, "write") as logger_write:

                task.logger.log(logging.CRITICAL, "a critical message")
                task.logger.log(logging.ERROR, "an error message")
                task.logger.log(logging.WARN, "a warning message")
                task.logger.log(logging.INFO, "an info message")
                task.logger.log(logging.DEBUG, "a debug message")

                task.logger.log(0, "a message with level 0")
                task.logger.log(1, "a message with level 1")
                task.logger.log(11, "a message with level 11")
                task.logger.log(21, "a message with level 21")
                task.logger.log(31, "a message with level 31")
                task.logger.log(41, "a message with level 41")

                logger_write.assert_has_calls(
                    (
                        mock.call("a critical message", "ERROR"),
                        mock.call("an error message", "ERROR"),
                        mock.call("a warning message", "WARN"),
                        mock.call("an info message", "INFO"),
                        mock.call("a debug message", "DEBUG"),
                        mock.call("a message with level 0", "DEBUG"),
                        mock.call("a message with level 1", "DEBUG"),
                        mock.call("a message with level 11", "DEBUG"),
                        mock.call("a message with level 21", "INFO"),
                        mock.call("a message with level 31", "WARN"),
                        mock.call("a message with level 41", "ERROR"),
                    )
                )

    def test_run_task_class_robot_logger(self):
        """Verify that 'run task class' uses the robot logger"""
        with mock.patch.object(self.cumulusci, "_run_task"):
            self.cumulusci.run_task_class(
                "cumulusci.tasks.command.Command", command="ls -l"
            )
            args, kwargs = self.cumulusci._run_task.call_args
            task = args[0]
            assert task.logger == robot.api.logger

    def test_run_unknown_task(self):
        with pytest.raises(TaskNotFoundError):
            self.cumulusci.run_task("bogus")

    def test_cross_project_task(self):
        """Verify that the cross-project task runs with the project config of the task
        See W-8891667
        """
        with temporary_dir() as tmpdir:
            tmpdir = Path(tmpdir).resolve()
            cumulusci_yml_path = tmpdir / "cumulusci.yml"
            with open(cumulusci_yml_path, "w+") as cumulusci_yml:
                self.project_config.sources["example"] = {"path": tmpdir}
                cumulusci_yml.write(
                    """
                    tasks:
                        whatever:
                            class_path: cumulusci.tasks.command.Command
                            options:
                                command: pwd
                    """
                )

            with mock.patch.object(self.cumulusci, "_run_task"):
                self.cumulusci.run_task("example:whatever")

                args, kwargs = self.cumulusci._run_task.call_args
                assert len(args) == 1

                # make sure it's not using the current project config
                # for the task, and that the config it _is_ using is
                # rooted in the directory we created
                task = args[0]
                assert task.project_config != self.cumulusci.project_config
                assert tmpdir == Path(task.project_config.repo_root)

    def test_find_access_token_alias_connected_orgs_multiple_users(self):
        """Verify exception when more than one username matches the criteria"""

        self.cumulusci.org.salesforce_client.query.side_effect = lambda query: {
            "records": [
                {"Username": "tester1@example.com"},
                {"Username": "tester2@example.com"},
            ]
        }
        with pytest.raises(
            Exception,
            match=(
                "More than one user matched the search critiera "
                "for org mock org "
                r"\(tester1@example.com, tester2@example.com\)."
            ),
        ):
            self.cumulusci._find_access_token(
                base_org=self.cumulusci.org, alias="tester1"
            )
            expected_query = "SELECT Username FROM User WHERE alias='tester1'"
            self.cumulusci.org.salesforce_client.query.assert_called_once_with(
                expected_query
            )

    def test_find_access_token_alias_connected_orgs_no_users(self):
        """Verify exception when no username matches the criteria"""

        self.cumulusci.org.salesforce_client.query.side_effect = lambda query: {
            "records": []
        }
        with pytest.raises(
            Exception,
            match=r"Couldn't find a username in org mock org for the specified user \(alias='tester1'\).",
        ):
            self.cumulusci._find_access_token(
                base_org=self.cumulusci.org, alias="tester1"
            )
            expected_query = "SELECT Username FROM User WHERE alias='tester1'"
            self.cumulusci.org.salesforce_client.query.assert_called_once_with(
                expected_query
            )

    def test_find_access_token_alias_connected_orgs_no_matching_org(self):
        self.cumulusci.org.salesforce_client.query.side_effect = lambda query: {
            "records": [
                {"Username": "tester1@example.com"},
            ]
        }

        token = self.cumulusci._find_access_token(
            base_org=self.cumulusci.org, alias="tester1"
        )
        assert token is None

    def test_find_access_token_happy_path(self):
        self.cumulusci.org.salesforce_client.query.side_effect = lambda query: {
            "records": [
                {"Username": "tester1@example.com"},
            ]
        }

        def get_org(org_name):
            configs = {
                "org1": DummyOrgConfig(
                    config={
                        "access_token": "super-secret-token-1",
                        "userinfo": {"preferred_username": "tester1@example.com"},
                    }
                ),
                "org2": DummyOrgConfig(
                    config={
                        "access_token": "super-secret-token-2",
                        "userinfo": {"preferred_username": "tester2@example.com"},
                    }
                ),
            }
            return configs.get(org_name, None)

        def list_orgs():
            return ["org1", "org2"]

        self.cumulusci.keychain.get_org = mock.Mock(wraps=get_org)
        self.cumulusci.keychain.list_orgs = mock.Mock(wraps=list_orgs)

        token = self.cumulusci._find_access_token(
            base_org=self.cumulusci.org, alias="tester1"
        )
        assert token == "super-secret-token-1"

    def test_login_url(self):
        """Verify that login_url by default returns the `start_url` of the org"""
        url = self.cumulusci.login_url()
        assert url == self.cumulusci.org.start_url

    def test_login_url_user_org_with_get_access_token(self):
        """Verify login_url branch when org has a get_access_token method

        This tests a specific branch were we're getting a url for a specific
        user and the org has a `get_access_token` method.
        """
        with mock.patch.object(
            self.cumulusci.org, "get_access_token", return_value="super-secret-token"
        ):

            url = self.cumulusci.login_url(username="test@example.com")
            self.cumulusci.org.get_access_token.assert_called_once_with(
                username="test@example.com"
            )
            assert (
                url
                == "https://test.example.com/secur/frontdoor.jsp?sid=super-secret-token"
            )

    def test_login_url_user_org_without_get_access_token(self):
        """Verify login_url branch when org DOES NOT have a get_access_token method

        This tests a specific branch were we're getting a url for a specific
        user and the org is missing the `get_access_token` method.
        """

        with mock.patch.object(self.cumulusci.org, "get_access_token"):
            self.cumulusci.org.get_access_token = None

            with mock.patch.object(
                self.cumulusci, "_find_access_token", return_value="super-secret-token"
            ):
                self.cumulusci._find_access_token.return_value = "super-secret-token"

                url = self.cumulusci.login_url(username="test@example.com")
                self.cumulusci._find_access_token.assert_called_with(
                    self.cumulusci.org, username="test@example.com"
                )
                assert (
                    url
                    == "https://test.example.com/secur/frontdoor.jsp?sid=super-secret-token"
                )

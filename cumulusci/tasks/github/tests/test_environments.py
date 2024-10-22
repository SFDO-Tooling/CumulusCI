import logging
import pytest
from rich.panel import Panel
from unittest import mock
from cumulusci.core.config import ServiceConfig, TaskConfig
from cumulusci.core.exceptions import GithubApiNotFoundError, OrgNotValidForTask
from cumulusci.tasks.github.environments import OrgToEnvironment
from cumulusci.tests.util import create_project_config


class TestOrgToEnvironment:
    @pytest.fixture
    def task(self):
        project_config = create_project_config(
            "TestRepo",
            "TestOwner",
            repo_commit="21e04cfe480f5293e2f7103eee8a5cbdb94f7982",
        )
        project_config.keychain.set_service(
            "github",
            "default",
            ServiceConfig(
                {"username": "test_user", "email": "test_email", "token": "test_token"}
            ),
        )
        task_config = TaskConfig({"options": {"environment_name": "test_env"}})
        task = OrgToEnvironment(project_config, task_config)
        task.repo = mock.Mock()
        task.repo.url = "https://api.github.com/repos/TestOwner/TestRepo"
        return task

    def test_init_task(self, task):
        task.get_repo = mock.Mock()
        task._init_task()
        assert task.console is not None
        assert task.repo is not None

    def test_get_or_create_environment(self, task):
        task.repo._put.return_value.json.return_value = {"name": "test_env"}

        environment = task._get_or_create_environment()

        assert environment["name"] == "test_env"
        task.repo._put.assert_called_once_with(
            "https://api.github.com/repos/TestOwner/TestRepo/environments/test_env"
        )

    def test_get_environment_variable(self, task):
        task.repo._get.return_value.json.return_value = {"value": "test_value"}

        value = task._get_environment_variable("TEST_VAR")

        assert value == "test_value"
        task.repo._get.assert_called_once_with(
            "https://api.github.com/repos/TestOwner/TestRepo/environments/test_env/variables/TEST_VAR"
        )

    def test_get_environment_variable_not_found(self, task):
        # Create a mock response with a status_code of 404
        mock_response = mock.Mock()
        mock_response.status_code = 404

        # Set the side effect of the _get method to raise GithubApiNotFoundError with the mock response
        task.repo._get.return_value = mock_response

        with pytest.raises(GithubApiNotFoundError) as exc_info:
            task._get_environment_variable("NON_EXISTENT_VAR")

    @mock.patch("cumulusci.tasks.github.environments.encrypt_secret")
    def test_update_secret(self, mock_encrypt_secret, task):
        mock_encrypt_secret.return_value = "encrypted_value"
        public_key = {"key": "test_key", "key_id": "test_key_id"}

        task._update_secret("TEST_SECRET", "test_value", public_key)

        task.repo._put.assert_called_once_with(
            "https://api.github.com/repos/TestOwner/TestRepo/environments/test_env/secrets/TEST_SECRET",
            json={"encrypted_value": "encrypted_value", "key_id": "test_key_id"},
        )

    @mock.patch("cumulusci.tasks.github.environments.encrypt_secret")
    def test_update_secret_404(self, mock_encrypt_secret, task):
        mock_encrypt_secret.return_value = "encrypted_value"
        task.repo._put.return_value = mock.Mock(status_code=404)
        public_key = {"key": "test_key", "key_id": "test_key_id"}

        with pytest.raises(GithubApiNotFoundError):
            task._update_secret("TEST_SECRET", "test_value", public_key)

    def test_create_variable(self, task):
        task._create_variable("TEST_VAR", "test_value")

        task.repo._post.assert_called_once_with(
            "https://api.github.com/repos/TestOwner/TestRepo/environments/test_env/variables",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            data={"name": "TEST_VAR", "value": "test_value"},
            json=True,
        )

    def test_create_variable_404(self, task):
        task.repo._post.return_value = mock.Mock(status_code=404)
        with pytest.raises(GithubApiNotFoundError):
            task._create_variable("TEST_VAR", "test_value")

    def test_create_variable_none_value(self, task):
        task._create_variable("TEST_VAR", None)

        task.repo._post.assert_called_once_with(
            "https://api.github.com/repos/TestOwner/TestRepo/environments/test_env/variables",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            data={"name": "TEST_VAR", "value": "None"},
            json=True,
        )

    def test_update_variable(self, task):
        task._update_variable("TEST_VAR", "new_value")

        task.repo._patch.assert_called_once_with(
            "https://api.github.com/repos/TestOwner/TestRepo/environments/test_env/variables/TEST_VAR",
            json={"value": "new_value"},
        )

    def test_update_variable_404(self, task):
        task.repo._patch.return_value = mock.Mock(status_code=404)
        with pytest.raises(GithubApiNotFoundError):
            task._update_variable("TEST_VAR", "new_value")

    def test_get_org_info_invalid_org(self, task):
        task.org_config = mock.Mock(spec=["name"])
        task.org_config.name = "TestOrg"
        with pytest.raises(OrgNotValidForTask):
            task._get_org_info()

    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._get_environment_variable"
    )
    def test_check_environment_no_org_id(self, mock_get_var, task):
        mock_get_var.side_effect = GithubApiNotFoundError("Not found")
        org_info = {"variables": {"ORG_ID": "test_org_id"}}

        assert task._check_environment(org_info) is True

    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._get_environment_variable"
    )
    def test_check_environment_matching_org_id(self, mock_get_var, task):
        mock_get_var.return_value = "test_org_id"
        org_info = {"variables": {"ORG_ID": "test_org_id"}}

        assert task._check_environment(org_info) is True

    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._get_environment_variable"
    )
    def test_check_environment_force_update(self, mock_get_var, task):
        mock_get_var.return_value = "old_org_id"
        org_info = {"variables": {"ORG_ID": "new_org_id"}}
        task.parsed_options.force_update = True

        assert task._check_environment(org_info) is True

    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._get_environment_variable"
    )
    def test_check_environment_mismatch_no_force(self, mock_get_var, task):
        mock_get_var.return_value = "old_org_id"
        org_info = {"variables": {"ORG_ID": "new_org_id"}}
        task.parsed_options.force_update = False

        assert task._check_environment(org_info) is False

    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._get_org_info")
    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._get_or_create_environment"
    )
    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._check_environment"
    )
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._update_secrets")
    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._update_variables"
    )
    def test_run_task(
        self,
        mock_update_variables,
        mock_update_secrets,
        mock_check_env,
        mock_get_or_create_env,
        mock_get_org_info,
        task,
    ):
        mock_get_org_info.return_value = {
            "secrets": {"ACCESS_TOKEN": "test_token"},
            "variables": {"ORG_ID": "test_org_id"},
        }
        mock_check_env.return_value = True
        task.console = mock.Mock()

        task._run_task()

        mock_get_org_info.assert_called_once()
        mock_get_or_create_env.assert_called_once()
        mock_check_env.assert_called_once()
        mock_update_secrets.assert_called_once_with(
            "test_env", {"ACCESS_TOKEN": "test_token"}
        )
        mock_update_variables.assert_called_once_with(
            "test_env", {"ORG_ID": "test_org_id"}
        )

        # Test console output
        task.console.print.assert_any_call("Collecting Salesforce org information...")
        task.console.print.assert_any_call(
            "Getting or Creating GitHub environment test_env..."
        )
        task.console.print.assert_any_call("Updating secrets ACCESS_TOKEN")
        task.console.print.assert_any_call("Updating variables ORG_ID")

    def test_get_environment_variables(self, task):
        task.repo._get.return_value.json.return_value = {
            "variables": [
                {"name": "VAR1", "value": "value1"},
                {"name": "VAR2", "value": "value2"},
            ]
        }

        variables = task._get_environment_variables()

        assert variables == {"VAR1": "value1", "VAR2": "value2"}
        task.repo._get.assert_called_once_with(
            "https://api.github.com/repos/TestOwner/TestRepo/environments/test_env/variables"
        )

    def test_get_public_key(self, task):
        task.repo._get.return_value.json.return_value = {
            "key": "test_public_key",
            "key_id": "test_key_id",
        }

        public_key = task._get_public_key()

        assert public_key == {"key": "test_public_key", "key_id": "test_key_id"}
        task.repo._get.assert_called_once_with(
            "https://api.github.com/repos/TestOwner/TestRepo/environments/test_env/secrets/public-key"
        )

    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._get_public_key")
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._update_secret")
    def test_update_secrets(self, mock_update_secret, mock_get_public_key, task):
        mock_get_public_key.return_value = {"key": "test_key", "key_id": "test_key_id"}
        secrets = {"SECRET1": "value1", "SECRET2": "value2"}

        task._update_secrets("test_env", secrets)

        mock_get_public_key.assert_called_once()
        assert mock_update_secret.call_count == 2
        mock_update_secret.assert_any_call(
            "SECRET1", "value1", {"key": "test_key", "key_id": "test_key_id"}
        )
        mock_update_secret.assert_any_call(
            "SECRET2", "value2", {"key": "test_key", "key_id": "test_key_id"}
        )

    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._get_environment_variables"
    )
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._update_variable")
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._create_variable")
    def test_update_variables(
        self, mock_create_variable, mock_update_variable, mock_get_variables, task
    ):
        mock_get_variables.return_value = {"EXISTING_VAR": "old_value"}
        variables = {"EXISTING_VAR": "new_value", "NEW_VAR": "value"}

        task._update_variables("test_env", variables)

        mock_get_variables.assert_called_once()
        mock_update_variable.assert_called_once_with("EXISTING_VAR", "new_value")
        mock_create_variable.assert_called_once_with("NEW_VAR", "value")

    def test_update_secret_environment_not_found(self, task):
        # Mock the _put method to raise GithubApiNotFoundError
        task.repo._put.side_effect = GithubApiNotFoundError("Environment not found")

        # Create a valid-looking public key (even though it won't be used due to the error)
        public_key = {
            "key": "hBT5WZEj8ZoOv6TYJsfWq7MxTEQopZO5/IT3ZCVQPzs=",  # This is a valid-looking but fake public key
            "key_id": "test_key_id",
        }

        with pytest.raises(GithubApiNotFoundError):
            task._update_secret("TEST_SECRET", "test_value", public_key)

        # Verify that the _put method was called with the correct arguments
        task.repo._put.assert_called_once_with(
            f"{task.repo.url}/environments/{task.parsed_options.environment_name}/secrets/TEST_SECRET",
            json={
                "encrypted_value": mock.ANY,  # We can't predict the exact encrypted value
                "key_id": "test_key_id",
            },
        )

    def test_get_org_info_success(self, task):
        mock_org_config = mock.Mock()
        mock_org_config.get_sfdx_info.return_value = {
            "access_token": "test_token",
            "instance_url": "https://test.salesforce.com",
            "org_id": "00D000000000001",
            "username": "test@example.com",
        }
        mock_org_config.config_name = "test_config"
        mock_org_config.instance_name = "test_instance"
        mock_org_config.namespace = "test_namespace"
        mock_org_config.namespaced = True
        mock_org_config.org_type = "sandbox"
        mock_org_config.scratch = False
        mock_org_config.config_file = "config/project-scratch-def.json"

        task.org_config = mock_org_config

        org_info = task._get_org_info()

        assert org_info == {
            "secrets": {
                "ACCESS_TOKEN": "test_token",
                "SFDX_AUTH_URL": "https://test.salesforce.com",
            },
            "variables": {
                "CUMULUSCI_CONFIG": "test_config",
                "INSTANCE_NAME": "test_instance",
                "INSTANCE_URL": "https://test.salesforce.com",
                "NAMESPACE": "test_namespace",
                "NAMESPACED": "True",
                "ORG_ID": "00D000000000001",
                "ORG_TYPE": "sandbox",
                "SCRATCH": "False",
                "SCRATCHDEF": "config/project-scratch-def.json",
                "USERNAME": "test@example.com",
            },
        }

    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._get_environment_variables"
    )
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._update_variable")
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._create_variable")
    def test_update_variables_empty_dict(
        self, mock_create_variable, mock_update_variable, mock_get_variables, task
    ):
        mock_get_variables.return_value = {}
        variables = {}

        task._update_variables("test_env", variables)

        mock_get_variables.assert_called_once()
        mock_update_variable.assert_not_called()
        mock_create_variable.assert_not_called()

    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._get_environment_variables"
    )
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._update_variable")
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._create_variable")
    def test_update_variables_all_up_to_date(
        self, mock_create_variable, mock_update_variable, mock_get_variables, task
    ):
        mock_get_variables.return_value = {"VAR1": "value1", "VAR2": "value2"}
        variables = {"VAR1": "value1", "VAR2": "value2"}

        task._update_variables("test_env", variables)

        mock_get_variables.assert_called_once()
        mock_update_variable.assert_not_called()
        mock_create_variable.assert_not_called()

    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._get_org_info")
    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._get_or_create_environment"
    )
    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._check_environment"
    )
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._update_secrets")
    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._update_variables"
    )
    def test_run_task_success_message(
        self,
        mock_update_variables,
        mock_update_secrets,
        mock_check_env,
        mock_get_or_create_env,
        mock_get_org_info,
        task,
    ):
        mock_get_org_info.return_value = {
            "secrets": {"ACCESS_TOKEN": "test_token"},
            "variables": {"ORG_ID": "test_org_id"},
        }
        mock_check_env.return_value = True
        task.console = mock.Mock()

        task._run_task()

        # Check that console.print was called with a Panel object
        success_panel_call = [
            call
            for call in task.console.print.call_args_list
            if isinstance(call[0][0], Panel)
        ]
        assert (
            len(success_panel_call) == 1
        ), "Expected one call to console.print with a Panel object"

        panel_obj = success_panel_call[0][0][0]
        assert isinstance(panel_obj, Panel)
        assert (
            panel_obj.title
            == f"GitHub Environment {task.parsed_options.environment_name} Updated Successfully"
        )
        assert panel_obj.border_style == "bold green"
        assert (
            "Successfully updated the GitHub environment with Salesforce org information."
            in panel_obj.renderable
        )

    def test_get_or_create_environment_error(self, task):
        task.repo._put.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            task._get_or_create_environment()

    def test_get_environment_variables_error(self, task):
        task.repo._get.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            task._get_environment_variables()

    def test_check_environment_no_update(self, task, caplog):
        task._get_environment_variable = mock.Mock(return_value="old_org_id")
        org_info = {"variables": {"ORG_ID": "new_org_id"}}
        task.parsed_options.force_update = False

        with caplog.at_level(logging.INFO):
            result = task._check_environment(org_info)

        assert result is False
        assert (
            "ORG_ID does not match and force_update is False, skipping update."
            in caplog.text
        )

    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._get_public_key")
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._update_secret")
    def test_update_secrets_logging(
        self, mock_update_secret, mock_get_public_key, task, caplog
    ):
        mock_get_public_key.return_value = {"key": "test_key", "key_id": "test_key_id"}
        secrets = {"SECRET1": "value1", "SECRET2": "value2"}

        with caplog.at_level(logging.INFO):
            task._update_secrets("test_env", secrets)

        assert "Updated secret SECRET1 in environment test_env" in caplog.text
        assert "Updated secret SECRET2 in environment test_env" in caplog.text

    @mock.patch(
        "cumulusci.tasks.github.environments.OrgToEnvironment._get_environment_variables"
    )
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._update_variable")
    @mock.patch("cumulusci.tasks.github.environments.OrgToEnvironment._create_variable")
    def test_update_variables_logging(
        self,
        mock_create_variable,
        mock_update_variable,
        mock_get_variables,
        task,
        caplog,
    ):
        mock_get_variables.return_value = {"EXISTING_VAR": "old_value"}
        variables = {"EXISTING_VAR": "new_value", "NEW_VAR": "value"}

        with caplog.at_level(logging.INFO):
            task._update_variables("test_env", variables)

        assert "Updating variable EXISTING_VAR in environment test_env" in caplog.text
        assert "Creating variable NEW_VAR in environment test_env" in caplog.text

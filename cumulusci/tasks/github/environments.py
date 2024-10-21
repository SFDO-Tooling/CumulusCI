from rich.console import Console
from rich.panel import Panel
from cumulusci.tasks.github.base import BaseGithubTask
from cumulusci.core.exceptions import GithubApiNotFoundError, OrgNotValidForTask
from cumulusci.core.github import encrypt_secret
from cumulusci.core.tasks import CCIOptions
from pydantic import Field


class OrgToGithubEnvironmentOptions(CCIOptions):
    """Pydantic model for task options."""

    environment_name: str = Field(
        ...,
        description="The name of the GitHub environment",
    )
    force_update: bool = Field(
        default=False,
        description="Force the update even if ORG_ID doesn't match",
    )


class OrgToEnvironment(BaseGithubTask):
    """Task to publish a local Salesforce org's information to a GitHub environment."""

    task_docs = """
    Publishes a local Salesforce org's information to a GitHub environment.
    """
    salesforce_task = True

    class Options(OrgToGithubEnvironmentOptions):
        pass

    def _init_task(self):
        super()._init_task()
        self.console = Console()
        self.repo = self.get_repo()

    def _run_task(self):
        self.console.print(f"Collecting Salesforce org information...")
        org_info = self._get_org_info()

        self.console.print(
            f"Getting or Creating GitHub environment {self.parsed_options.environment_name}..."
        )
        environment = self._get_or_create_environment()

        self._check_environment(org_info)

        self.console.print(f"Updating secrets {",".join(org_info['secrets'].keys())}")
        self._update_secrets(self.parsed_options.environment_name, org_info["secrets"])
        self.console.print(
            f"Updating variables {",".join(org_info['variables'].keys())}"
        )
        self._update_variables(
            self.parsed_options.environment_name, org_info["variables"]
        )

        self.console.print(
            Panel(
                "Successfully updated the GitHub environment with Salesforce org information.",
                title=f"GitHub Environment {self.parsed_options.environment_name} Updated Successfully",
                border_style="bold green",
            )
        )

    def _get_or_create_environment(self):
        """Upsert the GitHub Environment."""
        resp = self.repo._put(
            f"{self.repo.url}/environments/{self.parsed_options.environment_name}",
        )
        resp.raise_for_status()
        environment = resp.json()
        return environment

    def _get_environment_variable(self, key):
        """Retrieve the value of an environment variable."""
        resp = self.repo._get(
            f"{self.repo.url}/environments/{self.parsed_options.environment_name}/variables/{key}"
        )
        if resp.status_code == 404:
            raise GithubApiNotFoundError(f"Environment variable {key} not found.")
        resp.raise_for_status()
        return resp.json()["value"]

    def _get_environment_variables(self):
        """Retrieve all environment variables returning a dictionary of key/value."""
        resp = self.repo._get(
            f"{self.repo.url}/environments/{self.parsed_options.environment_name}/variables"
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            variable["name"]: variable["value"]
            for variable in data.get("variables", [])
        }

    def _check_environment(self, org_info):
        """Determine whether to update the GitHub environment."""
        try:
            env_org_id = self._get_environment_variable("ORG_ID")
        except GithubApiNotFoundError:
            self.logger.info("ORG_ID not found in environment, proceeding with update.")
            return True

        if env_org_id == org_info["variables"]["ORG_ID"]:
            self.logger.info("ORG_ID of environment matches, proceeding with update.")
            return True

        if self.parsed_options.force_update:
            self.logger.info(
                f"Force update is enabled, proceeding with update changing ORG_ID from {env_org_id} to {org_info['variables']['ORG_ID']}."
            )
            return True

        self.logger.info(
            "ORG_ID does not match and force_update is False, skipping update."
        )
        return False

    def _get_org_info(self) -> dict:
        """Collects the Salesforce org information needed for environment secrets and variables."""
        if not hasattr(self.org_config, "get_sfdx_info"):
            raise OrgNotValidForTask(
                f"Org {self.org_config.name} is not an sfdx org. Only sfdx orgs are supported. You can first connect the org to sfdx and then use `cci org import` to import it as an sfdx org."
            )
        sfdx_info = self.org_config.get_sfdx_info(verbose=True)
        # Temporarily add the verbose sfdx_info to the org_config so it can be used to construct org_info
        self.org_config._sfdx_info = sfdx_info
        org_info = {
            "secrets": {
                "ACCESS_TOKEN": sfdx_info["access_token"],
                "SFDX_AUTH_URL": sfdx_info["instance_url"],
            },
            "variables": {
                "CUMULUSCI_CONFIG": self.org_config.config_name,
                "INSTANCE_NAME": self.org_config.instance_name,
                "INSTANCE_URL": sfdx_info["instance_url"],
                "NAMESPACE": str(self.org_config.namespace),
                "NAMESPACED": str(self.org_config.namespaced),
                "ORG_ID": sfdx_info["org_id"],
                "ORG_TYPE": self.org_config.org_type,
                "SCRATCH": str(self.org_config.scratch),
                "SCRATCHDEF": self.org_config.config_file,
                "USERNAME": sfdx_info["username"],
            },
        }
        # Unset the verbose _sfdx_info from the org_config
        del self.org_config._sfdx_info
        return org_info

    def _get_public_key(self):
        """Retrieve the public key for the GitHub environment."""
        resp = self.repo._get(
            f"{self.repo.url}/environments/{self.parsed_options.environment_name}/secrets/public-key"
        )
        resp.raise_for_status()
        return resp.json()

    def _update_secret(self, key, value, public_key):
        """Update a secret in the GitHub environment."""
        encrypted_value = encrypt_secret(public_key["key"], value)
        resp = self.repo._put(
            f"{self.repo.url}/environments/{self.parsed_options.environment_name}/secrets/{key}",
            json={"encrypted_value": encrypted_value, "key_id": public_key["key_id"]},
        )
        if resp.status_code == 404:
            raise GithubApiNotFoundError(
                f"Environment {self.parsed_options.environment_name} not found."
            )
        resp.raise_for_status()
        return resp

    def _update_secrets(self, environment_name, secrets):
        """Create or update the GitHub environment with the Salesforce org info."""
        public_key = self._get_public_key()
        for key, value in secrets.items():
            self._update_secret(key, value, public_key)
            self.logger.info(f"Updated secret {key} in environment {environment_name}")

    def _create_variable(self, key, value):
        """Create a variable in the GitHub environment."""
        if value is None:
            value = "None"
        resp = self.repo._post(
            f"{self.repo.url}/environments/{self.parsed_options.environment_name}/variables",
            headers={
                "Accept": "application/vnd.github.v3+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            data={"name": key, "value": value},
            json=True,
        )
        if resp.status_code == 404:
            raise GithubApiNotFoundError(
                f"Environment {self.parsed_options.environment_name} not found."
            )
        resp.raise_for_status()
        return resp.json()

    def _update_variable(self, key, value):
        """Update a variable in the GitHub environment."""
        resp = self.repo._patch(
            f"{self.repo.url}/environments/{self.parsed_options.environment_name}/variables/{key}",
            json={"value": value},
        )
        if resp.status_code == 404:
            raise GithubApiNotFoundError(
                f"Environment {self.parsed_options.environment_name} not found."
            )
        resp.raise_for_status()
        return resp.json()

    def _update_variables(self, environment_name, variables):
        """Create or update the GitHub environment with the Salesforce org info."""
        existing_variables = self._get_environment_variables()
        for key, value in variables.items():
            if key in existing_variables:
                if existing_variables[key] == value:
                    self.logger.info(
                        f"Variable {key} in environment {environment_name} is already up to date."
                    )
                else:
                    self.logger.info(
                        f"Updating variable {key} in environment {environment_name}"
                    )
                    self._update_variable(key, value)
            else:
                self.logger.info(
                    f"Creating variable {key} in environment {environment_name}"
                )
                self._create_variable(key, value)

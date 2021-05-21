import json
import requests
import zipfile

from collections import defaultdict
from pathlib import Path

from cumulusci.core.exceptions import DeploymentException
from cumulusci.utils import temporary_dir
from cumulusci.utils.http.requests_utils import safe_json_from_response
from .base import BaseMarketingCloudTask

MCPM_ENDPOINT = "https://mc-package-manager.herokuapp.com"

PAYLOAD_CONFIG_VALUES = {"preserveCategories": True}

PAYLOAD_NAMESPACE_VALUES = {
    "category": "",
    "prepend": "",
    "append": "",
    "timestamp": True,
}


class MarketingCloudDeployTask(BaseMarketingCloudTask):

    task_options = {
        "package_zip_file": {
            "description": "Path to the package zipfile that will be deployed.",
            "required": True,
        }
    }

    def _run_task(self):
        pkg_zip_file = Path(self.options["package_zip_file"])
        if not pkg_zip_file.is_file():
            self.logger.error(f"Package zip file not valid: {pkg_zip_file.name}")
            return

        with temporary_dir(chdir=False) as temp_dir:
            with zipfile.ZipFile(pkg_zip_file) as zf:
                zf.extractall(temp_dir)
                payload = self._construct_payload(Path(temp_dir))

        self.headers = {
            "Authorization": f"Bearer {self.mc_config.access_token}",
            "SFMC-TSSD": self.mc_config.tssd,
        }
        response = requests.post(
            f"{MCPM_ENDPOINT}/deployments",
            json=payload,
            headers=self.headers,
        )
        result = safe_json_from_response(response)
        self.job_id = result["info"]["id"]
        self.logger.info(f"Started job {self.job_id}")
        self._poll()

    def _poll_action(self):
        """
        Poll something and process the response.
        Set `self.poll_complete = True` to break polling loop.
        """
        response = requests.get(
            f"{MCPM_ENDPOINT}/deployments/{self.job_id}", headers=self.headers
        )
        result = safe_json_from_response(response)
        self.logger.info(f"Waiting [{result['status']}]...")
        if result["status"] == "DONE":
            self.poll_complete = True
            self._validate_response(result)

    def _construct_payload(self, dir_path):
        dir_path = Path(dir_path)
        assert dir_path.is_dir(), "package_directory must be a directory"

        payload = defaultdict(lambda: defaultdict(dict))
        payload["namespace"] = PAYLOAD_NAMESPACE_VALUES
        payload["config"] = PAYLOAD_CONFIG_VALUES

        with open(dir_path / "references.json", "r") as f:
            payload["references"] = json.load(f)

        with open(dir_path / "input.json", "r") as f:
            payload["input"] = json.load(f)

        entities_dir = Path(f"{dir_path}/entities")
        for item in entities_dir.glob("**/*.json"):
            if item.is_file():
                entity_name = item.parent.name
                entity_id = item.stem
                with open(item, "r") as f:
                    payload["entities"][entity_name][entity_id] = json.load(f)

        return payload

    def _validate_response(self, deploy_info: dict):
        """Checks for any errors present in the response to the deploy request.
        Displays errors if present, else informs use that the deployment was successful."""
        has_error = False
        for entity, info in deploy_info["entities"].items():
            if not info:
                continue

            for entity_id, info in info.items():
                if info["status"] != "SUCCESS":
                    has_error = True
                    self.logger.error(
                        f"Failed to deploy {entity}/{entity_id}. Status: {info['status']}. Issues: {info['issues']}"
                    )

        if has_error:
            raise DeploymentException("Marketing Cloud reported deployment failures.")

        self.logger.info("Deployment completed successfully.")

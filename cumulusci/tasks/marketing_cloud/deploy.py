import json
import requests
import zipfile

from collections import defaultdict
from pathlib import Path

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.utils import temporary_dir
from .base import BaseMarketingCloudTask

MC_DEPLOY_ENDPOINT = "https://mc-package-manager.herokuapp.com/api/spm/deploy"

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

        response = requests.post(
            MC_DEPLOY_ENDPOINT,
            json=payload,
            headers={
                "Authorization": f"Bearer {self.mc_config.access_token}",
                "SFMC-TSSD": self.mc_config.tssd,
            },
        )

        self._validate_response(response)

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

    def _validate_response(self, response: requests.Response):
        """Checks for any errors present in the response to the deploy request.
        Displays errors if present, else informs use that the deployment was successful."""

        if response.status_code != 200:
            raise CumulusCIException(response.text)

        has_error = False
        deploy_info = json.loads(response.text)
        for entity, info in deploy_info["entities"].items():
            if not info:
                continue

            for entity_id, info in info.items():
                if info["status"] != "SUCCESS":
                    has_error = True
                    self.logger.error(
                        f"Failed to deploy {entity}/{entity_id}. Status: {info['status']}. Issues: {info['issues']}"
                    )

        if not has_error:
            self.logger.info("Deployment completed successfully.")

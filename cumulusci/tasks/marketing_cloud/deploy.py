import json
import uuid
import zipfile
from collections import defaultdict
from pathlib import Path

import requests

from cumulusci.core.debug import get_debug_mode
from cumulusci.core.exceptions import DeploymentException
from cumulusci.core.utils import process_list_of_pairs_dict_arg
from cumulusci.utils import temporary_dir
from cumulusci.utils.http.requests_utils import safe_json_from_response

from .base import BaseMarketingCloudTask

MCPM_ENDPOINT = "https://spf.{}.marketingcloudapps.com/api"

PAYLOAD_CONFIG_VALUES = {"preserveCategories": True}

PAYLOAD_NAMESPACE_VALUES = {
    "category": "",
    "prepend": "",
    "append": "",
    "timestamp": True,
}

IN_PROGRESS_STATUS = "IN_PROGRESS"
FINISHED_STATUSES = ("DONE",)
ERROR_STATUSES = ("FATAL_ERROR", "ERROR")

UNKNOWN_STATUS_MESSAGE = "Received unknown deploy status: {}"


class MarketingCloudDeployTask(BaseMarketingCloudTask):

    task_options = {
        "package_zip_file": {
            "description": "Path to the package zipfile that will be deployed.",
            "required": True,
        },
        "custom_inputs": {
            "description": "Specify custom inputs to the deployment task. Takes a mapping from input key to input value (e.g. 'companyName:Acme,companyWebsite:https://www.salesforce.org:8080').",
            "required": False,
        },
        "name": {
            "description": "The name to give to this particular deploy call. Defaults to a universally unique identifier.",
            "required": False,
        },
        "endpoint": {
            "description": "Override the default endpoint for the Marketing Cloud package manager API (optional)",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        self.debug_mode = get_debug_mode()
        super()._init_options(kwargs)
        custom_inputs = self.options.get("custom_inputs")
        self.custom_inputs = (
            process_list_of_pairs_dict_arg(custom_inputs) if custom_inputs else None
        )

    def _run_task(self):
        pkg_zip_file = Path(self.options["package_zip_file"])
        if not pkg_zip_file.is_file():
            self.logger.error(f"Package zip file not valid: {pkg_zip_file.name}")
            return

        with temporary_dir(chdir=False) as temp_dir:
            with zipfile.ZipFile(pkg_zip_file) as zf:
                zf.extractall(temp_dir)
                payload = self._construct_payload(Path(temp_dir), self.custom_inputs)

        self.headers = {
            "Authorization": f"Bearer {self.mc_config.access_token}",
            "SFMC-TSSD": self.mc_config.tssd,
        }
        custom_endpoint = self.options.get("endpoint")
        self.endpoint = (
            custom_endpoint
            if custom_endpoint
            else MCPM_ENDPOINT.format(self.get_mc_stack_key())
        )

        self.logger.info(f"Deploying package to: {self.endpoint}/deployments")
        response = requests.post(
            f"{self.endpoint}/deployments",
            json=payload,
            headers=self.headers,
        )
        response_data = safe_json_from_response(response)

        self.job_id = response_data["id"]
        self.logger.info(f"Started deploy job with Id: {self.job_id}")
        self._poll()

    def _poll_action(self):
        """
        Poll something and process the response.
        Set `self.poll_complete = True` to break polling loop.
        """
        response = requests.get(
            f"{self.endpoint}/deployments/{self.job_id}", headers=self.headers
        )
        response_data = safe_json_from_response(response)
        deploy_status = response_data["status"]
        self.logger.info(f"Deployment status is: {deploy_status}")

        if deploy_status != IN_PROGRESS_STATUS:
            self._process_completed_deploy(response_data)

    def _process_completed_deploy(self, response_data: dict):
        deploy_status = response_data["status"]
        assert (
            deploy_status != IN_PROGRESS_STATUS
        ), "Deploy should be in a completed state before processing."

        if deploy_status in FINISHED_STATUSES:
            self.poll_complete = True
            self._validate_response(response_data)
        elif deploy_status in ERROR_STATUSES:
            self.poll_complete = True
            self._report_error(response_data)
        else:
            self.logger.error(UNKNOWN_STATUS_MESSAGE.format(deploy_status))
            self.poll_complete = True
            self._report_error(response_data)

    def _construct_payload(self, dir_path, custom_inputs=None):
        dir_path = Path(dir_path)
        assert dir_path.is_dir(), "package_directory must be a directory"

        payload = defaultdict(lambda: defaultdict(dict))
        payload["namespace"] = PAYLOAD_NAMESPACE_VALUES
        payload["config"] = PAYLOAD_CONFIG_VALUES
        payload["name"] = self.options.get("name", str(uuid.uuid4()))

        try:
            with open(dir_path / "info.json", "r") as f:
                info_json = json.load(f)
                model_version = info_json.get("modelVersion", 1)

                self.logger.debug(
                    f"Setting Marketing Cloud Package Manager modelVersion to: {model_version}"
                )
                payload["modelVersion"] = model_version

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
        except FileNotFoundError as e:
            msg = f"Expected file not found in provided package zip file: {e.filename.split('/')[-1]}"
            raise DeploymentException(msg)

        if custom_inputs:
            payload = self._add_custom_inputs_to_payload(custom_inputs, payload)

        if self.debug_mode:  # pragma: nocover
            self.logger.debug(f"Payload:\n{json.dumps(payload)}")

        return payload

    def _add_custom_inputs_to_payload(self, custom_inputs, payload):
        for input_name, value in custom_inputs.items():
            found = False
            for input in payload["input"]:
                if input["key"] == input_name:
                    input["value"] = value
                    found = True
                    break

            if not found:
                raise DeploymentException(
                    f"Custom input of key {input_name} not found in package."
                )

        return payload

    def _validate_response(self, deploy_info: dict):
        """Checks for any errors present in the response to the deploy request.
        Displays errors if present, else informs use that the deployment was successful."""
        has_error = False
        for entity, info in deploy_info["entities"].items():
            if not info:
                continue

            for entity_id, info in info.items():
                if info["status"] not in ("SUCCESS", "REUSED"):
                    has_error = True
                    self.logger.error(
                        f"Failed to deploy {entity}/{entity_id}. Status: {info['status']}. Issues: {info['issues']}"
                    )

        if has_error:
            raise DeploymentException("Marketing Cloud reported deployment failures.")

        self.logger.info("Deployment completed successfully.")

    def _report_error(self, response_data: dict):
        deploy_status = response_data["status"]
        self.logger.error(
            f"Received status of: {deploy_status}. Received the following data from Marketing Cloud:\n{response_data}^"
        )
        raise DeploymentException(
            f"Marketing Cloud deploy finished with status of: {deploy_status}"
        )

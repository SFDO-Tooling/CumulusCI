import json
import uuid
import zipfile
from collections import defaultdict
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

import requests

from cumulusci.core.debug import get_debug_mode
from cumulusci.core.exceptions import DeploymentException
from cumulusci.core.utils import process_list_of_pairs_dict_arg
from cumulusci.utils import temporary_dir
from cumulusci.utils.http.requests_utils import safe_json_from_response

from .base import BaseMarketingCloudTask

MCPM_BASE_ENDPOINT = "https://spf.{}.marketingcloudapps.com/api"

MCPM_JOB_ID_HEADER = "x-mcpm-job-id"

PAYLOAD_CONFIG_VALUES = {"preserveCategories": True}

PAYLOAD_NAMESPACE_VALUES = {
    "category": "",
    "prepend": "",
    "append": "",
    "timestamp": True,
}

IN_PROGRESS_STATUSES = ("NOT_STARTED", "IN_PROGRESS")
FINISHED_STATUSES = ("DONE",)
ERROR_STATUSES = ("FATAL_ERROR", "ERROR")


UNKNOWN_STATUS_MESSAGE = "Received unknown deploy status: {}"


class PollAction(Enum):
    validating = "VALIDATING"
    deploying = "DEPLOYING"


class MarketingCloudDeployTask(BaseMarketingCloudTask):
    # This task executes multiple polling loops.
    # This enables the task to determine which endpoints should be polled.
    current_action: Optional[PollAction] = None
    validation_not_found_count = 0
    job_name: Optional[str]

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
        # Marketing Cloud validation _requires_ a 2-second static polling interval
        self.poll_interval_s = 2

        pkg_zip_file = Path(self.options["package_zip_file"])
        if not pkg_zip_file.is_file():
            self.logger.error(f"Package zip file not valid: {pkg_zip_file.name}")
            return

        with temporary_dir(chdir=False) as temp_dir:
            with zipfile.ZipFile(pkg_zip_file) as zf:
                zf.extractall(temp_dir)
                payload = self._construct_payload(Path(temp_dir), self.custom_inputs)

        # These initialization steps are not done in _init_options()
        # because they use MC authorization. We don't want to freeze
        # the responses.
        endpoint_option = self.options.get("endpoint")
        self.endpoint = endpoint_option or MCPM_BASE_ENDPOINT.format(
            self.get_mc_stack_key()
        )

        self.headers = {
            "Authorization": f"Bearer {self.mc_config.access_token}",
            "SFMC-TSSD": self.mc_config.tssd,
        }

        self._validate_package(payload)
        self._reset_poll()

        payload = self._update_payload_entities_with_actions(
            payload,
        )
        self._deploy_package(payload)

    def _construct_payload(self, dir_path, custom_inputs=None):
        dir_path = Path(dir_path)
        assert dir_path.is_dir(), "package_directory must be a directory"

        payload = defaultdict(lambda: defaultdict(dict))
        payload["namespace"] = PAYLOAD_NAMESPACE_VALUES
        payload["config"] = PAYLOAD_CONFIG_VALUES
        payload["name"] = self.job_name = self.options.get("name", str(uuid.uuid4()))  # type: ignore

        try:
            with open(dir_path / "info.json", "r") as f:
                info_json = json.load(f)
                model_version = info_json.get("modelVersion", "1")

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

    def _validate_package(self, payload: Dict) -> None:
        """Sends the payload to MC for validation.
        Returns a dict of allowable actions for the target MC instance."""
        self.current_action = PollAction.validating
        self.logger.info(f"Validating package at: {self.endpoint}/validate")
        assert self.job_name
        response = requests.post(
            f"{self.endpoint}/validate",
            json=payload,
            headers={
                MCPM_JOB_ID_HEADER: self.job_name,
                **self.headers,
            },
        )
        response.raise_for_status()
        response_data = safe_json_from_response(response)
        self.validate_id = response_data["id"]
        self.logger.info(f"Started package validation with Id: {self.validate_id}")
        self._poll()

    def _update_payload_entities_with_actions(self, payload: Dict) -> Dict:
        """Include available entity action returned from the validation
        endpoint into the payload used for package deployment."""

        for entity_type in payload["entities"]:
            this_entity_type = payload["entities"][entity_type]
            for entity_id in this_entity_type:
                this_entity = payload["entities"][entity_type][entity_id]
                action = self.action_for_entity(entity_type, entity_id)
                this_entity["action"] = action

        if self.debug_mode:
            self.logger.debug(f"Payload updated with actions:\n{json.dumps(payload)}")

        return payload

    def action_for_entity(self, entity: str, entity_id: str) -> Optional[Dict]:
        """Fetch the corresponding action for the given entity with the specified Id"""
        try:
            for action_info in self.validation_response["entities"][entity][entity_id][
                "actions"
            ].values():
                if action_info["available"]:
                    return action_info
        except KeyError:
            # if no actions are defined for this entity just move on
            pass

    def _deploy_package(self, payload: Dict) -> None:
        self.current_action = PollAction.deploying
        self.logger.info(f"Deploying package to: {self.endpoint}/deployments")
        response = requests.post(
            f"{self.endpoint}/deployments",
            json=payload,
            headers=self.headers,
        )
        response.raise_for_status()
        response_data = safe_json_from_response(response)
        self.deploy_id = response_data["id"]
        self.logger.info(f"Started package deploy with Id: {self.validate_id}")
        self._poll()

    def _poll_action(self) -> None:
        """
        Poll based on the current action being taken.
        """
        if self.current_action == PollAction.validating:
            self._poll_validating()
        elif self.current_action == PollAction.deploying:
            self._poll_deploying()
        else:
            raise Exception(
                f"PollAction {self.current_action} does not have a polling handler defined."
            )

    def _poll_validating(self) -> None:
        assert self.job_name
        response = requests.get(
            f"{self.endpoint}/validate/{self.validate_id}",
            headers={MCPM_JOB_ID_HEADER: self.job_name, **self.headers},
        )
        response_data = safe_json_from_response(response)
        validation_status = response_data["status"]
        self.logger.info(f"Validation status is: {validation_status}")

        # Handle eccentricities of Marketing Cloud validation polling.
        # We may get back a NOT_FOUND result if our request is routed
        # to the wrong pod by MC. This should be fixed, but hasn't been
        # deployed to all MC stacks yet.

        # Observed behavior is that response switches between NOT_FOUND
        # and IN_PROGRESS. We'll track these responses and fail the job
        # only if we consistently receive NOT_FOUND.

        # TODO: add a timeout.
        if validation_status == "NOT_FOUND":
            self.validation_not_found_count += 1
            if self.validation_not_found_count > 10:
                raise DeploymentException(
                    f"Unable to find status on validation: {self.validate_id}"
                )
        else:
            # Reset if we get back a result other than NOT_FOUND
            self.validation_not_found_count = 0
            if validation_status not in IN_PROGRESS_STATUSES:
                self.poll_complete = True
                if self.debug_mode:  # pragma: nocover
                    self.logger.debug(
                        f"Validation Response:\n{json.dumps(response_data)}"
                    )
                self.validation_response = response_data

    def _poll_deploying(self) -> None:
        response = requests.get(
            f"{self.endpoint}/deployments/{self.deploy_id}", headers=self.headers
        )
        response_data = safe_json_from_response(response)
        deploy_status = response_data["status"]
        self.logger.info(f"Deployment status is: {deploy_status}")

        if deploy_status not in IN_PROGRESS_STATUSES:
            self._process_completed_deploy(response_data)

    def _poll_update_interval(self):
        # Marketing Cloud validation _requires_ a 2-second static polling interval.
        # Override the base class to remove backoff.
        pass

    def _process_completed_deploy(self, response_data: Dict):
        deploy_status = response_data["status"]
        assert (
            deploy_status != IN_PROGRESS_STATUSES
        ), "Deploy should be in a completed state before processing."

        self.poll_complete = True
        if deploy_status in FINISHED_STATUSES:
            self._validate_response(response_data)
        elif deploy_status in ERROR_STATUSES:
            self._report_error(response_data)
        else:
            self.logger.error(UNKNOWN_STATUS_MESSAGE.format(deploy_status))
            self._report_error(response_data)

    def _validate_response(self, deploy_info: Dict) -> None:
        """Checks for any errors present in the response to the deploy request.
        Displays errors if present, else informs use that the deployment was successful.
        """
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

        self.logger.info(f"Deployment ({self.deploy_id}) completed successfully.")

    def _report_error(self, response_data: Dict) -> None:
        deploy_status = response_data["status"]
        self.logger.error(
            f"Received status of: {deploy_status}. Received the following data from Marketing Cloud:\n{json.dumps(response_data)}"
        )
        raise DeploymentException(
            f"Marketing Cloud deploy finished with status of: {deploy_status}"
        )

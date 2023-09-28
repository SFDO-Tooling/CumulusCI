import base64
import io
import json
import os
import time
import uuid
import zipfile
from typing import List, Union

import requests

PARENT_DIR_NAME = "metadata"


class RestDeploy:
    def __init__(
        self,
        task,
        package_zip: str,
        purge_on_delete: Union[bool, str, None],
        check_only: bool,
        test_level: Union[str, None],
        run_tests: List[str],
    ):
        # Initialize instance variables and configuration options
        self.api_version = task.project_config.project__package__api_version
        self.task = task
        assert package_zip, "Package zip should not be None"
        if purge_on_delete is None:
            purge_on_delete = True
        self._set_purge_on_delete(purge_on_delete)
        self.check_only = "true" if check_only else "false"
        self.test_level = test_level
        self.package_zip = package_zip
        self.run_tests = run_tests or []

    def __call__(self):
        self._boundary = str(uuid.uuid4())
        url = f"{self.task.org_config.instance_url}/services/data/v{self.api_version}/metadata/deployRequest"
        headers = {
            "Authorization": f"Bearer {self.task.org_config.access_token}",
            "Content-Type": f"multipart/form-data; boundary={self._boundary}",
        }

        # Prepare deployment options as JSON payload
        deploy_options = {
            "deployOptions": {
                "allowMissingFiles": False,
                "autoUpdatePackage": False,
                "checkOnly": self.check_only,
                "ignoreWarnings": False,
                "performRetrieve": False,
                "purgeOnDelete": self.purge_on_delete,
                "rollbackOnError": False,
                "runTests": self.run_tests,
                "singlePackage": False,
                "testLevel": self.test_level,
            }
        }
        json_payload = json.dumps(deploy_options)

        # Construct the multipart/form-data request body
        body = (
            f"--{self._boundary}\r\n"
            f'Content-Disposition: form-data; name="json"\r\n'
            f"Content-Type: application/json\r\n\r\n"
            f"{json_payload}\r\n"
            f"--{self._boundary}\r\n"
            f'Content-Disposition: form-data; name="file"; filename="metadata.zip"\r\n'
            f"Content-Type: application/zip\r\n\r\n"
        ).encode("utf-8")
        body += self._reformat_zip(self.package_zip)
        body += f"\r\n--{self._boundary}--\r\n".encode("utf-8")

        response = requests.post(url, headers=headers, data=body)
        response_json = response.json()

        if response.status_code == 201:
            self.task.logger.info("Deployment request successful")
            deploy_request_id = response_json["id"]
            self._monitor_deploy_status(deploy_request_id)
        else:
            self.task.logger.error(
                f"Deployment request failed with status code {response.status_code}"
            )

    # Set the purge_on_delete attribute based on org type
    def _set_purge_on_delete(self, purge_on_delete):
        if not purge_on_delete or purge_on_delete == "false":
            self.purge_on_delete = "false"
        else:
            self.purge_on_delete = "true"
        # Disable purge on delete entirely for non sandbox or DE orgs as it is
        # not allowed
        org_type = self.task.org_config.org_type
        is_sandbox = self.task.org_config.is_sandbox
        if org_type != "Developer Edition" and not is_sandbox:
            self.purge_on_delete = "false"

    # Monitor the deployment status and log progress
    def _monitor_deploy_status(self, deploy_request_id):
        url = f"{self.task.org_config.instance_url}/services/data/v{self.api_version}/metadata/deployRequest/{deploy_request_id}?includeDetails=true"
        headers = {"Authorization": f"Bearer {self.task.org_config.access_token}"}

        while True:
            response = requests.get(url, headers=headers)
            response_json = response.json()
            self.task.logger.info(
                f"Deployment {response_json['deployResult']['status']}"
            )

            if response_json["deployResult"]["status"] not in ["InProgress", "Pending"]:
                # Handle the case when status has Failed
                if response_json["deployResult"]["status"] == "Failed":
                    for failure in response_json["deployResult"]["details"][
                        "componentFailures"
                    ]:
                        self.task.logger.error(self._construct_error_message(failure))
                return
            time.sleep(5)

    # Reformat the package zip file to include parent directory
    def _reformat_zip(self, package_zip):
        zip_bytes = base64.b64decode(package_zip)
        zip_stream = io.BytesIO(zip_bytes)
        new_zip_stream = io.BytesIO()

        with zipfile.ZipFile(zip_stream, "r") as zip_ref:
            with zipfile.ZipFile(new_zip_stream, "w") as new_zip_ref:
                for item in zip_ref.infolist():
                    # Choice of name for parent directory is irrelevant to functioning
                    new_item_name = os.path.join(PARENT_DIR_NAME, item.filename)
                    file_content = zip_ref.read(item.filename)
                    new_zip_ref.writestr(new_item_name, file_content)

        new_zip_bytes = new_zip_stream.getvalue()
        return new_zip_bytes

    # Construct an error message from deployment failure details
    def _construct_error_message(self, failure):
        error_message = f"{str.upper(failure['problemType'])} in file {failure['fileName'][len(PARENT_DIR_NAME)+len('/'):]}: {failure['problem']}"

        if failure["lineNumber"] and failure["columnNumber"]:
            error_message += (
                f" at line {failure['lineNumber']}:{failure['columnNumber']}"
            )

        return error_message

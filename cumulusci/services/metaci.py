from datetime import datetime
from pathlib import Path
from random import randint
from tempfile import TemporaryDirectory

import requests
from pydantic import BaseModel

from cumulusci.core.config import ScratchOrgConfig, TaskConfig
from cumulusci.core.sfdx import sfdx
from cumulusci.utils.http.requests_utils import safe_json_from_response


class OrgPoolPayload(BaseModel):
    org_name: str
    frozen_steps: list[dict]
    task_class: str = None
    repo_url: str
    days: int = None  # not implemented


class MetaCIService:
    """Base class for tasks that talk to MetaDeploy's API."""

    def __init__(self, runtime):
        metaci_service = runtime.project_config.keychain.get_service("metaci")
        self.base_url = metaci_service.url
        self.api = requests.Session()
        self.api.headers["Authorization"] = "token {}".format(metaci_service.token)

    def call_api(self, method, path, **kwargs):
        metaci_url = self.base_url + path
        response = self.api.request(method, metaci_url, **kwargs)
        if response.status_code == 400:
            raise requests.exceptions.HTTPError(response.content)
        return safe_json_from_response(response)

    def fetch_from_org_pool(self, payload):
        result = self.call_api(
            method="POST", path="/orgs/request_pooled_org", data=payload.json()
        )
        if not result:
            return None
        result["date_created"] = datetime.fromisoformat(result["date_created"])
        assert "error" not in result, result
        return result


def fetch_pooled_org(runtime, coordinator, org_name):
    task_class_name = (
        "cumulusci.tasks.salesforce.update_dependencies.UpdateDependencies"
    )
    repo = runtime.project_config.repo_url.removesuffix(".git")
    step = coordinator.steps[0]
    task = step.task_class(
        step.project_config,
        TaskConfig(step.task_config),
        name=step.task_name,
    )
    org_pool_payload = OrgPoolPayload(
        frozen_steps=task.freeze(step),
        task_class=task_class_name,
        repo_url=repo,
        org_name=org_name,
    )
    print(f"I have the payload {org_pool_payload.json()}")
    # create call to metaci to check org pool payload availability
    metaci = MetaCIService(runtime)
    org_config_dict = metaci.fetch_from_org_pool(payload=org_pool_payload)

    if org_config_dict:
        print(
            "FETCHED", org_config_dict.keys(), org_config_dict["username"].split("@"[0])
        )
        org_config = ScratchOrgConfig(
            org_config_dict, org_name, runtime.keychain, global_org=False
        )
        runtime.keychain._set_org(
            org_config,
            False,
        )
        # sfdx_auth_url = org_config_dict["sfdx_auth_url"]
        # with TemporaryDirectory() as t:
        #     filename = Path(t) / str(randint(0, 100000000))
        #     filename.write_text(sfdx_auth_url)

        #     sfdx(
        #         f"auth:sfdxurl:store -f {filename}",
        #         log_note="Saving scratch org",
        #         check_return=True,
        #     )

        return org_config
    else:
        return None

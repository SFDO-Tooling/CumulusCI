from datetime import datetime

import requests
from pydantic import BaseModel

from cumulusci.core.config import ScratchOrgConfig, TaskConfig
from cumulusci.utils.http.requests_utils import safe_json_from_response


class OrgPoolPayload(BaseModel):
    frozen_steps: list
    task_class: str = None
    repo_url: str
    org_name: str
    days: int = None  # not implemented


class OrgPoolResult(BaseModel):
    org: dict = None
    error: dict = None


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
        result = self.call_api(method="POST", path="/org-pool", data=payload.json())
        result["date_created"] = datetime.fromisoformat(result["date_created"])
        assert "error" not in result, result
        return result or None


def fetch_pooled_org(runtime, coordinator, org_name):
    task_class_name = (
        "cumulusci.tasks.salesforce.update_dependencies.UpdateDependencies"
    )
    repo = runtime.project_config.repo_url
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
    # create call to metaci to check org pool payload availability
    metaci = MetaCIService(runtime)
    org_config_dict = metaci.fetch_from_org_pool(payload=org_pool_payload)
    print("FETCHED", org_config_dict.keys(), org_config_dict["username"].split("@"[0]))

    if org_config_dict:
        org_config = ScratchOrgConfig(
            org_config_dict, org_name, runtime.keychain, global_org=False
        )
        runtime.keychain._set_org(
            org_config,
            False,
        )
        return org_config
    else:
        return None

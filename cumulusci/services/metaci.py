from datetime import datetime
import json
import requests


from cumulusci.utils.http.requests_utils import safe_json_from_response
from pydantic import BaseModel


class OrgPoolPayload(BaseModel):
    task_config: dict
    task_class: str = None
    repo_url: str
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
        response = safe_json_from_response(response)

    def fetch_from_org_pool(self, payload):
        result = self.call_api(method="POST", path="/org-pool", json=payload)
        result["date_created"] = datetime.fromisoformat(result["date_created"])
        assert "error" not in result, result
        return result or None

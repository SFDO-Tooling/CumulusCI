"""Calls to the MetaDeploy REST API."""
import functools
from typing import Optional, Union

from pydantic.error_wrappers import ValidationError
from requests.models import Response
from requests.sessions import Session

from cumulusci.core.config import ServiceConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.metadeploy.models import (
    MetaDeployPlan,
    PlanTemplate,
    Product,
    Slug,
    Version,
)
from cumulusci.utils.http.requests_utils import safe_json_from_response


def make_api_session(metadeploy_service: ServiceConfig) -> Session:
    """
    Given a MetaDeploy ServiceConfig, returns a requests.Session with
    authorization headers and service.base_url set.
    """
    base_url: str = metadeploy_service.url

    patched_session = Session()
    patched_session.headers["Authorization"] = f"token {metadeploy_service.token}"

    def patched_request(base, func, method, url, *args, **kwargs):
        """Call requests.request with base_url prepended."""
        base_url = base + url.replace(base, "", 1)
        return func(method, base_url, *args, **kwargs)

    patched_session.request = functools.partial(
        patched_request, base_url, patched_session.request
    )

    return patched_session


class MetaDeployAPI:
    def __init__(self, metadeploy_service: ServiceConfig) -> None:
        self.session: Session = make_api_session(metadeploy_service=metadeploy_service)

    def _create(self, obj: str, json: dict) -> dict:
        response: Response = self.session.post(obj, json=json)
        return safe_json_from_response(response)

    def _find(self, obj: str, query: Union[dict, str]) -> Optional[dict]:
        response: Response = self.session.get(obj, params=query)
        result: dict = safe_json_from_response(response)

        try:
            return result["data"][0]
        except IndexError:
            return None
        except KeyError:
            raise CumulusCIException(
                "CumulusCI received an unexpected response from MetaDeploy. "
                "Ensure that your MetaDeploy service is configured with the Admin API URL, which "
                "ends in /rest, and that your authentication token is valid."
            ) from None

    def create_plan(self, plan: MetaDeployPlan) -> MetaDeployPlan:
        return MetaDeployPlan.parse_obj(
            self._create("/plans", json=plan.dict(exclude_none=True))
        )

    def create_plan_template(self, template: PlanTemplate) -> PlanTemplate:
        return PlanTemplate.parse_obj(
            self._create("/plantemplates", json=template.dict())
        )

    def create_plan_slug(self, slug: Slug) -> Slug:
        return Slug.parse_obj(
            self._create("/planslug", json=slug.dict(include={"slug", "parent"}))
        )

    def create_version(self, version: dict) -> Version:
        return Version.parse_obj(self._create("/versions", json=version))

    def find_product(self, repo_url: str) -> Product:
        try:
            product_json = self._find("/products", {"repo_url": repo_url})
            return Product.parse_obj(product_json)
        except ValidationError:
            raise CumulusCIException(
                f"No product found in MetaDeploy with repo URL {repo_url}"
            ) from None

    def find_plan_template(self, query: dict) -> Optional[PlanTemplate]:
        if template_json := self._find("/plantemplates", query):
            return PlanTemplate.parse_obj(template_json)

    def find_version(self, query: dict) -> Optional[Version]:
        if version_json := self._find("/versions", query):
            return Version.parse_obj(version_json)

    def update_version(self, pk: Union[int, str]) -> dict:
        response: Response = self.session.patch(
            f"/versions/{pk}", json={"is_listed": True}
        )
        return safe_json_from_response(response)

    def update_lang_translation(self, lang: str, labels: dict) -> dict:
        response: Response = self.session.patch(f"/translations/{lang}", json=labels)
        return safe_json_from_response(response)

    def find_or_create_plan_template(
        self, product_id: str, plan_template_maybe: PlanTemplate, slug: str
    ) -> PlanTemplate:
        query: dict = {"product": product_id, "name": plan_template_maybe.name}
        existing_plan_template: Optional[PlanTemplate] = self.find_plan_template(query)

        if existing_plan_template:
            return existing_plan_template

        plan_template = self.create_plan_template(plan_template_maybe)
        _ = self.create_plan_slug(
            Slug.parse_obj({"slug": slug, "parent": plan_template.url})
        )
        return plan_template

    def find_or_create_version(
        self, product_id: str, version_maybe: Version
    ) -> Version:
        query: dict = {"product": product_id, "label": version_maybe.label}
        existing_version: Optional[Version] = self.find_version(query)
        return existing_version or self.create_version(version_maybe.dict())

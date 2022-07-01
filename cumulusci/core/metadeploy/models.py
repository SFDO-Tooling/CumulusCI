"""MetaDeploy domain models"""

import enum
from typing import Dict, List, Literal, Mapping, Optional

from pydantic import BaseModel, root_validator, validator
from pydantic.fields import Field
from pydantic.networks import AnyUrl
from pydantic.types import NonNegativeInt

from cumulusci.core.metadeploy.labels import (
    INSTALL_VERSION_RE,
    METADEPLOY_DIR,
    METADEPLOY_LABELS,
)


def labels_to_field_descriptions(labels: Mapping[str, str]) -> Dict[str, dict]:
    """Convert a LabelMap to pydantic field descriptions"""
    return {
        field: {"description": description} for field, description in labels.items()
    }


class SupportedOrgs(str, enum.Enum):
    BOTH = "Both"
    PERSISTENT = "Persistent"
    SCRATCH = "Scratch"


class MetaDeployModel(BaseModel):
    id: Optional[str]
    url: Optional[AnyUrl]


class FrozenModel(BaseModel):
    class Config:
        allow_mutation = False


class PreflightCheck(BaseModel):
    when: Optional[str] = None
    action: Optional[str] = None
    message: Optional[str] = None

    class Config:
        fields = {"message": {"description": "shown if validation fails"}}


class FrozenSpec(FrozenModel):
    github: AnyUrl
    commit: str
    description: str


class FrozenTaskConfig(FrozenModel):
    options: dict
    checks: List[PreflightCheck] = []


class FrozenStep(FrozenModel):
    is_recommended: bool = True
    is_required: bool = True
    kind: Literal["data", "managed", "metadata", "onetime", "other"] = "other"
    description: Optional[str] = None
    name: str
    path: str
    source: Optional[FrozenSpec]
    step_num: str
    task_class: str
    task_config: FrozenTaskConfig
    url: Optional[AnyUrl] = None


class PublisherOptions(FrozenModel):
    tag: Optional[str] = None
    commit: Optional[str] = None
    plan: Optional[str] = None
    dry_run: bool = False
    publish: bool = False
    labels_path: str = METADEPLOY_DIR

    @root_validator
    def check_tag_or_commit(cls, values):
        if not values.get("tag") and not values.get("commit"):
            raise ValueError("You must specify either the tag or commit option.")
        return values

    @validator("publish")
    def check_publish(cls, publish, values):
        return not values["dry_run"] and publish


class Product(MetaDeployModel):
    title: str
    short_description: str
    description: str
    click_through_agreement: str
    error_message: str
    slug: str
    color: Optional[str]
    image: Optional[str]
    icon_url: Optional[str]
    slds_icon_category: Optional[
        Literal["", "action", "custom", "doctype", "standard", "utility"]
    ]
    slds_icon_name: Optional[str]
    repo_url: Optional[str]
    is_listed: Optional[str]
    order_key: Optional[str]
    layout: Optional[Literal["Default", "Card"]]
    visible_to: Optional[str]
    category: Optional[str]


class Slug(MetaDeployModel):
    parent: AnyUrl
    is_active: Optional[bool] = None
    slug: str = Field(..., max_length=50)


class Version(MetaDeployModel):
    id: Optional[str] = None
    url: Optional[str] = None
    label: str
    is_production: bool = False
    is_listed: bool = False
    commit_ish: str
    product: AnyUrl


class PlanTemplate(MetaDeployModel):
    preflight_message: str = ""
    post_install_message: str = ""
    error_message: str = ""
    name: Optional[str] = Field(None, max_length=100)
    product: AnyUrl
    regression_test_opt_out: bool = False
    preflight_checks: List[PreflightCheck] = Field([], alias="checks")


class MetaDeployPlan(MetaDeployModel):
    id: Optional[str] = None
    commit_ish: Optional[str] = None
    is_listed: bool = True
    order_key: Optional[NonNegativeInt] = None
    plan_template: Optional[AnyUrl] = None
    post_install_message: str = Field("", exclude=True)
    preflight_checks: List[PreflightCheck] = Field([], alias="checks")
    preflight_message: str = Field("", exclude=True)
    slug: Optional[str]
    steps: List[FrozenStep] = []
    supported_orgs: SupportedOrgs = SupportedOrgs.PERSISTENT
    tier: Literal["primary", "secondary", "additional"]
    title: str
    url: Optional[AnyUrl] = None
    version: AnyUrl
    visible_to: Optional[str]

    class Config:
        fields = labels_to_field_descriptions(METADEPLOY_LABELS["plan"])

    @validator("supported_orgs", pre=True)
    def map_supported_orgs(cls, input):
        """Given a list of plan.allowed_org_providers return the value that
        corresponds to the `supported_orgs` field on the MetaDeploy Plan
        """
        if not input:
            return SupportedOrgs.PERSISTENT
        try:
            return SupportedOrgs(input)
        except ValueError:
            lookup: Mapping[frozenset, str] = {
                frozenset(["user"]): SupportedOrgs.PERSISTENT,
                frozenset(["devhub"]): SupportedOrgs.SCRATCH,
                frozenset(["devhub", "user"]): SupportedOrgs.BOTH,
            }
            return lookup[frozenset(input)]

import pytest
from pydantic import ValidationError

from cumulusci.core.metadeploy.labels import METADEPLOY_LABELS
from cumulusci.core.metadeploy.models import (
    FrozenStep,
    MetaDeployPlan,
    PreflightCheck,
    PublisherOptions,
    SupportedOrgs,
)

pytestmark = pytest.mark.metadeploy


@pytest.mark.parametrize(
    "input,expected",
    zip(
        [
            ["user", "devhub"],
            ["user"],
            ["devhub"],
        ],
        list(SupportedOrgs),
    ),
)
def test_supported_orgs_validation_map(input, expected, simple_plan_dict):
    del simple_plan_dict["supported_orgs"]
    result = MetaDeployPlan(supported_orgs=input, **simple_plan_dict)
    assert expected == result.supported_orgs


def test_supported_orgs_validation_empty(simple_plan_dict):
    del simple_plan_dict["supported_orgs"]
    persistent = MetaDeployPlan(supported_orgs=None, **simple_plan_dict)
    assert persistent.supported_orgs == SupportedOrgs.PERSISTENT

    empty = MetaDeployPlan(supported_orgs=[], **simple_plan_dict)
    assert empty.supported_orgs == SupportedOrgs.PERSISTENT


def test_publisher_options_tag_validation():
    with pytest.raises(
        ValidationError, match="You must specify either the tag or commit option."
    ):
        PublisherOptions(plan="slug", dry_run=True, publish=True)


def test_publisher_options_no_publish_on_dry_run():
    opts: PublisherOptions = PublisherOptions(
        plan="slug", dry_run=True, publish=True, tag="v2.0"
    )
    assert not opts.publish

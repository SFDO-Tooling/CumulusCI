from unittest.mock import MagicMock

import pytest
import responses
from simple_salesforce.exceptions import SalesforceMalformedRequest

from cumulusci.tasks.preflight.settings import CheckMyDomainActive, CheckSettingsValue
from cumulusci.tasks.salesforce.tests.util import create_task

JSON_RESPONSE = {
    "records": [{"IntVal": 3, "FloatVal": 3.0, "BoolVal": True, "StringVal": "foo"}],
    "done": True,
    "totalSize": 1,
}


@responses.activate
@pytest.mark.parametrize(
    "settings_field,value,outcome",
    [
        ("IntVal", 3, True),
        ("FloatVal", 3.0, True),
        ("BoolVal", "true", True),
        ("StringVal", "foo", True),
        ("StringVal", "bad", False),
    ],
)
def test_check_settings(settings_field, value, outcome, sf_url):
    task = create_task(
        CheckSettingsValue,
        {
            "settings_type": "ChatterSettings",
            "settings_field": settings_field,
            "value": value,
        },
    )
    responses.add(
        "GET",
        sf_url(task.org_config)
        + f"/tooling/query/?q=SELECT+{settings_field}+FROM+ChatterSettings",
        json=JSON_RESPONSE,
    )

    task()

    assert task.return_values is outcome


@responses.activate
def test_check_settings__no_settings(sf_url):
    task = create_task(
        CheckSettingsValue,
        {
            "settings_type": "ChatterSettings",
            "settings_field": "Foo",
            "value": True,
        },
    )
    responses.add(
        "GET",
        sf_url(task.org_config) + "/tooling/query/?q=SELECT+Foo+FROM+ChatterSettings",
        json={"records": []},
    )

    task()

    assert task.return_values is False


@responses.activate
def test_check_settings__failure(sf_url):
    task = create_task(
        CheckSettingsValue,
        {
            "settings_type": "NoSettings",
            "settings_field": "Test",
            "value": True,
            "treat_missing_as_failure": True,
        },
    )
    responses.add(
        "GET",
        status=400,
        url=sf_url(task.org_config) + "/tooling/query/?q=SELECT+Test+FROM+NoSettings",
        json={},
    )

    task()

    assert task.return_values is False


@responses.activate
def test_check_settings__exception(sf_url):
    task = create_task(
        CheckSettingsValue,
        {
            "settings_type": "NoSettings",
            "settings_field": "Test",
            "value": True,
        },
    )
    responses.add(
        "GET",
        status=400,
        url=sf_url(task.org_config) + "/tooling/query/?q=SELECT+Test+FROM+NoSettings",
        json={},
    )
    with pytest.raises(SalesforceMalformedRequest):
        task()

    assert task.return_values is False


@pytest.mark.parametrize(
    "my_domain,outcome",
    [
        ("https://cumulusci.my.salesforce.com", True),
        ("https://cumulusci.cloudforce.com", True),
        ("https://na44.salesforce.com", False),
    ],
)
def test_my_domain_check(my_domain, outcome):
    org_config = MagicMock()
    org_config.instance_url = my_domain
    task = create_task(CheckMyDomainActive, {}, org_config=org_config)
    task()

    assert task.return_values is outcome

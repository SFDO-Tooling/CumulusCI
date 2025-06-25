import pytest
import responses
from responses.matchers import json_params_matcher

from cumulusci.core.config.org_config import OrgConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.salesforce.enable_prediction import EnablePrediction
from cumulusci.tests.util import CURRENT_SF_API_VERSION, DummyKeychain

from .util import create_task


@pytest.fixture
def task():
    return create_task(
        EnablePrediction,
        {"api_names": ["test_prediction_v0", "test_prediction_2_v0"]},
        org_config=OrgConfig(
            {"instance_url": "https://test-dev-ed.my.salesforce.com"},
            "test",
            keychain=DummyKeychain(),
        ),
    )


@pytest.fixture
def mock_oauth():
    with responses.RequestsMock() as rsps:
        rsps.add(
            "POST",
            "https://test-dev-ed.my.salesforce.com/services/oauth2/token",
            json={
                "access_token": "TOKEN",
                "instance_url": "https://test-dev-ed.my.salesforce.com",
            },
        )
        rsps.add(
            "GET",
            url="https://test-dev-ed.my.salesforce.com/services/oauth2/userinfo",
            json={},
            status=200,
        )
        rsps.add(
            "GET",
            url="https://test-dev-ed.my.salesforce.com/services/data",
            json=[
                {
                    "label": "Summer '21",
                    "url": f"/services/data/v{CURRENT_SF_API_VERSION}",
                    "version": CURRENT_SF_API_VERSION,
                }
            ],
            status=200,
        )
        rsps.add(
            "GET",
            f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/sobjects/Organization/",
            json={
                "OrganizationType": "Developer",
                "IsSandbox": False,
                "InstanceName": "NA149",
                "NamespacePrefix": None,
            },
        )
        rsps.add(
            "GET",
            url="https://test-dev-ed.my.salesforce.com/services/data/v63.0/tooling/query/?q=SELECT%20SubscriberPackage.Id,%20SubscriberPackage.Name,%20SubscriberPackage.NamespacePrefix,%20SubscriberPackageVersionId%20FROM%20InstalledSubscriberPackage",
            json={"records": []},
            status=200,
        )

        yield rsps


def test_run_task(mock_oauth, task):
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/?q=SELECT+Id+FROM+MLPredictionDefinition+WHERE+DeveloperName+%3D+%27test_prediction_v0%27",
        json={"totalSize": 1, "records": [{"Id": "001"}]},
    )
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/?q=SELECT+Id+FROM+MLPredictionDefinition+WHERE+DeveloperName+%3D+%27test_prediction_2_v0%27",
        json={"totalSize": 1, "records": [{"Id": "002"}]},
    )
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/001",
        json={"Metadata": {"status": "Draft"}},
    )
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/002",
        json={"Metadata": {"status": "Draft"}},
    )
    mock_oauth.add(
        method="PATCH",
        url=f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/001",
        match=[json_params_matcher({"Metadata": {"status": "Enabled"}})],
    )
    mock_oauth.add(
        method="PATCH",
        url=f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/002",
        match=[json_params_matcher({"Metadata": {"status": "Enabled"}})],
    )

    task()


def test_run_task__not_found_exception(mock_oauth, task):
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/?q=SELECT+Id+FROM+MLPredictionDefinition+WHERE+DeveloperName+%3D+%27test_prediction_v0%27",
        json={"totalSize": 0, "records": []},
    )

    with pytest.raises(CumulusCIException) as e:
        task()
        assert "not found" in str(e)


def test_run_task__failed_update_exception(mock_oauth, task):
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/?q=SELECT+Id+FROM+MLPredictionDefinition+WHERE+DeveloperName+%3D+%27test_prediction_v0%27",
        json={"totalSize": 1, "records": [{"Id": "001"}]},
    )
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/001",
        json={"Metadata": {"status": "Draft"}},
    )
    mock_oauth.add(
        method="PATCH",
        url=f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/001",
        status=400,
    )

    with pytest.raises(CumulusCIException):
        task()


def test_run_task__namespaced_org(mock_oauth, task):
    task.options["namespaced_org"] = True
    task.options["namespace_inject"] = "foo"
    task.options["api_names"] = [
        "%%%NAMESPACED_ORG%%%test_prediction_v0",
        "%%%NAMESPACED_ORG%%%test_prediction_2_v0",
    ]

    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/?q=SELECT+Id+FROM+MLPredictionDefinition+WHERE+DeveloperName+%3D+%27foo__test_prediction_v0%27",
        json={"totalSize": 1, "records": [{"Id": "001"}]},
    )
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/?q=SELECT+Id+FROM+MLPredictionDefinition+WHERE+DeveloperName+%3D+%27foo__test_prediction_2_v0%27",
        json={"totalSize": 1, "records": [{"Id": "002"}]},
    )
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/001",
        json={"Metadata": {"status": "Draft"}},
    )
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/002",
        json={"Metadata": {"status": "Draft"}},
    )
    mock_oauth.add(
        method="PATCH",
        url=f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/001",
        match=[json_params_matcher({"Metadata": {"status": "Enabled"}})],
    )
    mock_oauth.add(
        method="PATCH",
        url=f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/002",
        match=[json_params_matcher({"Metadata": {"status": "Enabled"}})],
    )

    mock_oauth.replace(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/sobjects/Organization/",
        json={
            "OrganizationType": "Developer",
            "IsSandbox": False,
            "InstanceName": "NA149",
            "NamespacePrefix": "foo",
        },
    )

    task()


def test_run_task__managed_org(mock_oauth, task):
    task.options["managed"] = True
    task.options["namespace_inject"] = "foo"
    task.options["api_names"] = [
        "%%%NAMESPACE%%%test_prediction_v0",
        "%%%NAMESPACE%%%test_prediction_2_v0",
    ]

    mock_oauth.remove(
        "GET",
        url="https://test-dev-ed.my.salesforce.com/services/data/v63.0/tooling/query/?q=SELECT%20SubscriberPackage.Id,%20SubscriberPackage.Name,%20SubscriberPackage.NamespacePrefix,%20SubscriberPackageVersionId%20FROM%20InstalledSubscriberPackage",
    )

    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/?q=SELECT+Id+FROM+MLPredictionDefinition+WHERE+DeveloperName+%3D+%27foo__test_prediction_v0%27",
        json={"totalSize": 1, "records": [{"Id": "001"}]},
    )
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/query/?q=SELECT+Id+FROM+MLPredictionDefinition+WHERE+DeveloperName+%3D+%27foo__test_prediction_2_v0%27",
        json={"totalSize": 1, "records": [{"Id": "002"}]},
    )
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/001",
        json={"Metadata": {"status": "Draft"}},
    )
    mock_oauth.add(
        "GET",
        f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/002",
        json={"Metadata": {"status": "Draft"}},
    )
    mock_oauth.add(
        method="PATCH",
        url=f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/001",
        match=[json_params_matcher({"Metadata": {"status": "Enabled"}})],
    )
    mock_oauth.add(
        method="PATCH",
        url=f"https://test-dev-ed.my.salesforce.com/services/data/v{CURRENT_SF_API_VERSION}/tooling/sobjects/MLPredictionDefinition/002",
        match=[json_params_matcher({"Metadata": {"status": "Enabled"}})],
    )

    task()

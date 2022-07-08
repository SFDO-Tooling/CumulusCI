import pytest
import responses
from requests.models import Response
from requests.sessions import Session
from responses import matchers

from cumulusci.core.config import ServiceConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.metadeploy.api import MetaDeployAPI, make_api_session

pytestmark = pytest.mark.metadeploy
DEFAULT_REST_URL: str = "https://metadeploy.example.com/api/rest"
DEFAULT_TOKEN: str = "37b003aee9bdd744a6618e9fe12"


@pytest.fixture
def default_api_client():
    return MetaDeployAPI(
        metadeploy_service=ServiceConfig(
            {"url": DEFAULT_REST_URL, "token": DEFAULT_TOKEN}
        )
    )


@pytest.fixture
def auth_header_matcher():
    return matchers.header_matcher({"Authorization": f"token {DEFAULT_TOKEN}"})


@responses.activate
def test_make_api(auth_header_matcher):
    expected_result: dict = {"data": [1]}
    responses.add(
        "GET",
        f"{DEFAULT_REST_URL}/resource",
        json=expected_result,
        match=[auth_header_matcher],
    )
    responses.add(
        "POST",
        f"{DEFAULT_REST_URL}/resource",
        json=expected_result,
        match=[auth_header_matcher],
    )
    service: ServiceConfig = ServiceConfig(
        {"url": f"{DEFAULT_REST_URL}", "token": DEFAULT_TOKEN}
    )
    api_session: Session = make_api_session(service)
    resp: Response = api_session.get("/resource")
    result: dict = resp.json()
    assert result == expected_result
    _ = api_session.get(f"{DEFAULT_REST_URL}/resource")

    assert responses.assert_call_count(f"{DEFAULT_REST_URL}/resource", 2) is True


def test_find_product(default_api_client, auth_header_matcher):
    params = {"repo_url": "https://api.github.com/repos/TestOwner/TestRepo"}
    payload = {
        "data": [
            {
                "id": "abcdef",
                "url": "https://EXISTING_PRODUCT",
                "slug": "existing",
            }
        ]
    }

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.GET,
            url=f"{DEFAULT_REST_URL}/products",
            match=(auth_header_matcher, matchers.query_param_matcher(params)),
            json=payload,
        )

        product: dict = default_api_client.find_product(params["repo_url"])
    assert product == payload["data"][0]


def test_find_product__api_err(default_api_client, auth_header_matcher):
    params = {"repo_url": "https://api.github.com/repos/TestOwner/MISSING"}
    payload = {"result": []}

    with pytest.raises(CumulusCIException, match="unexpected response"):
        with responses.RequestsMock() as rsps:
            rsps.add(
                method=responses.GET,
                url=f"{DEFAULT_REST_URL}/products",
                match=(auth_header_matcher, matchers.query_param_matcher(params)),
                json=payload,
            )

            default_api_client.find_product(params["repo_url"])


def test_create_plan(default_api_client, auth_header_matcher):
    payload = {"url": f"{DEFAULT_REST_URL}/plans/1"}
    plan = {
        "is_listed": True,
        "plan_template": "https://foo.example.com/1",
        "post_install_message_additional": "",
        "preflight_message_additional": "",
        "steps": [],
        "supported_orgs": "persistent",
        "tier": "primary",
        "title": "Install Tubulator 1.0",
        "version": f"{DEFAULT_REST_URL}/version/1",
        "visible_to": None,
    }

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.POST,
            url=f"{DEFAULT_REST_URL}/plans",
            match=(auth_header_matcher, matchers.json_params_matcher(plan)),
            status=201,
            json=payload,
        )
        result = default_api_client.create_plan(plan)
    assert result == payload


def test_find_version(default_api_client, auth_header_matcher):
    query = {"product": "bDcaVz", "label": "1.0"}
    payload = {"data": [{"url": "http://EXISTING_VERSION"}]}

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.GET,
            url=f"{DEFAULT_REST_URL}/versions",
            match=(auth_header_matcher, matchers.query_param_matcher(query)),
            json=payload,
        )

        result = default_api_client.find_version(query)

    assert result == payload["data"][0]


def test_find_version_missing_none(default_api_client, auth_header_matcher):
    query = {"product": "bDcaVz", "label": "1.0"}
    payload = {"data": []}

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.GET,
            url=f"{DEFAULT_REST_URL}/versions",
            match=(auth_header_matcher, matchers.query_param_matcher(query)),
            json=payload,
        )

        result = default_api_client.find_version(query)

    assert result is None


def test_create_version(default_api_client, auth_header_matcher):
    version = {
        "product": f"{DEFAULT_REST_URL}/product/foo",
        "label": "1.0",
        "description": "",
        "is_production": True,
        "commit_ish": "tag_or_sha",
        "is_listed": False,
    }
    payload = {"url": f"http://{DEFAULT_REST_URL}/versions/1", "id": 1}

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.POST,
            url=f"{DEFAULT_REST_URL}/versions",
            match=(auth_header_matcher, matchers.json_params_matcher(version)),
            status=201,
            json=payload,
        )

        version = default_api_client.create_version(version)

    assert version == payload


def test_publish_version(default_api_client, auth_header_matcher):
    vers = {"is_listed": True}
    pk = "XG4pVvD"
    payload = {"url": f"http://{DEFAULT_REST_URL}/versions/{pk}", "id": pk}

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.PATCH,
            url=f"{DEFAULT_REST_URL}/versions/{pk}",
            match=(auth_header_matcher, matchers.json_params_matcher(vers)),
            json=payload,
        )

        updated_version = default_api_client.update_version(pk)
    assert payload == updated_version


def test_find_plan_template(default_api_client, auth_header_matcher):
    query = {"product": "bDcaVz", "name": "Shinra"}
    payload = {"data": [{"url": "http://existing_template"}]}

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.GET,
            url=f"{DEFAULT_REST_URL}/plantemplates",
            match=(auth_header_matcher, matchers.query_param_matcher(query)),
            json=payload,
        )

        template = default_api_client.find_plan_template(query)

    assert template == payload["data"][0]


def test_create_plan_template(default_api_client, auth_header_matcher):
    template = {
        "name": "plan_name",
        "product": "product",
        "preflight_message": "",
        "post_install_message": "",
        "error_message": "oops",
    }
    payload = {"url": "http://EXISTING_VERSION"}

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.POST,
            url=f"{DEFAULT_REST_URL}/plantemplates",
            match=(auth_header_matcher, matchers.json_params_matcher(template)),
            status=201,
            json=payload,
        )

        created_template = default_api_client.create_plan_template(template)

    assert created_template == payload


def test_create_plan_slug(default_api_client, auth_header_matcher):
    slug = {"slug": "plan_name", "parent": "product"}
    payload = {"url": "http://EXISTING_VERSION"}

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.POST,
            url=f"{DEFAULT_REST_URL}/planslug",
            match=(auth_header_matcher, matchers.json_params_matcher(slug)),
            status=201,
            json=payload,
        )

        created_slug = default_api_client.create_plan_slug(slug)

    assert created_slug == payload


def test_publish_labels(default_api_client, auth_header_matcher):
    lang = "en_us"
    labels = {
        "title": "name of product",
        "error_message": "shown after failed installation (markdown)",
    }
    payload = {}

    with responses.RequestsMock() as rsps:
        rsps.add(
            method=responses.PATCH,
            url=f"{DEFAULT_REST_URL}/translations/{lang}",
            match=(auth_header_matcher, matchers.json_params_matcher(labels)),
            json=payload,
        )

        updated_txn = default_api_client.update_lang_translation(lang, labels)
    assert payload == updated_txn

#!/usr/bin/env python3
import pytest

from cumulusci.core.metadeploy.models import (
    MetaDeployPlan,
    PlanTemplate,
    Product,
    Version,
)


@pytest.fixture
def product_dict():
    return {
        "id": "abcdef",
        "url": "https://EXISTING_PRODUCT",
        "title": "Education Data Architecture (EDA)",
        "short_description": "The Foundation for the Connected Campus",
        "description": "## Welcome to the EDA installer!",
        "click_through_agreement": "Ladies and Gentlemen of the jury, I'm just a Caveman.",
        "error_message": "",
        "slug": "existing",
    }


@pytest.fixture
def version_dict():
    return {
        "url": "http://EXISTING_VERSION",
        "id": "OkAgPpL",
        "label": "1.0",
        "created_at": "2022-06-30T21:15:15.390046Z",
        "is_production": True,
        "commit_ish": "release/1.0",
        "is_listed": True,
        "product": "http://localhost:8080/admin/rest/products/abcdef",
    }


@pytest.fixture
def plantemplate_dict():
    return {
        "url": "http://localhost:8080/admin/rest/plantemplates/1",
        "id": "1",
        "preflight_message": "Preflight message consists of generic product message and step pre-check info — run in one operation before the install begins. Preflight includes the name of what is being installed. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s.",
        "post_install_message": "Success! You installed it.",
        "error_message": "",
        "name": "Full Install for Product With Useful Data, Version 0.2.0",
        "regression_test_opt_out": False,
        "product": "http://localhost:8080/admin/rest/products/GLN6Ppx",
    }


@pytest.fixture
def simple_plan_dict():
    return {
        "url": "http://localhost:8080/admin/rest/plans/GLN6Ppx",
        "id": "GLN6Ppx",
        "steps": [],
        "title": "Full Install",
        "preflight_message_additional": "",
        "post_install_message_additional": "",
        "commit_ish": None,
        "order_key": 0,
        "tier": "primary",
        "is_listed": True,
        "preflight_checks": [],
        "supported_orgs": "Persistent",
        "org_config_name": "release",
        "scratch_org_duration_override": None,
        "created_at": "2022-06-30T21:15:11.629638Z",
        "visible_to": None,
        "plan_template": "http://localhost:8080/admin/rest/plantemplates/1",
        "version": "http://localhost:8080/admin/rest/versions/GLN6Ppx",
    }


@pytest.fixture
def product_model(product_dict):
    return Product.parse_obj(product_dict)


@pytest.fixture
def version_model(version_dict):
    return Version.parse_obj(version_dict)


@pytest.fixture
def plantemplate_model(plantemplate_dict):
    return PlanTemplate.parse_obj(plantemplate_dict)


@pytest.fixture
def plan_model(simple_plan_dict):
    return MetaDeployPlan.parse_obj(simple_plan_dict)

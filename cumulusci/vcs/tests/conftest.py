import pytest

from cumulusci.core.config import BaseProjectConfig, ServiceConfig, UniversalConfig


@pytest.fixture()
def project_config():
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(universal_config, config={"no_yaml": True})
    project_config.config["services"] = {
        "github": {
            "attributes": {"name": {"required": True}, "password": {}},
        },
        "github_enterprise": {
            "attributes": {"name": {"required": True}, "password": {}},
        },
        "test_service": {
            "attributes": {"name": {"required": True}, "password": {}},
        },
    }
    project_config.project = {"name": "TestProject"}
    return project_config


@pytest.fixture
def key():
    return "0123456789123456"


@pytest.fixture
def service_config():
    return ServiceConfig(
        {
            "name": "bar@baz.biz",
            "password": "test123",
            "username": "username",
            "email": "bar@baz.biz",
            "token": "abcdef",
        },
        name="alias",
    )

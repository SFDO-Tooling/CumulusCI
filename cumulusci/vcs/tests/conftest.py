import pytest

from cumulusci.core.config import BaseProjectConfig, ServiceConfig, UniversalConfig


@pytest.fixture()
def project_config():
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(universal_config, config={"no_yaml": True})
    project_config.config["services"] = {
        "github": {
            "attributes": {"name": {"required": True}, "password": {}},
            "class_path": "cumulusci.vcs.tests.dummy_service.ConcreteVCSService",
        },
        "github_enterprise": {
            "attributes": {"name": {"required": True}, "password": {}},
            "class_path": "cumulusci.vcs.tests.dummy.ConcreteVCSService",
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

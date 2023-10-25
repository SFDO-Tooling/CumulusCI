from unittest import mock

import pytest

from cumulusci.core.config import OrgConfig


@pytest.fixture
def devhub_config():
    org_config = OrgConfig(
        {"instance_url": "https://devhub.my.salesforce.com", "access_token": "token"},
        "devhub",
    )
    org_config.refresh_oauth_token = mock.Mock()

    return org_config


@pytest.fixture
def org_config():
    org_config = OrgConfig(
        {
            "instance_url": "https://scratch.my.salesforce.com",
            "access_token": "token",
            "config_file": "orgs/scratch_def.json",
        },
        "dev",
    )
    org_config.refresh_oauth_token = mock.Mock()
    return org_config

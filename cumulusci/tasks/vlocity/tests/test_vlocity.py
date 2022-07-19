from unittest import mock

import pytest

from cumulusci.core.config import TaskConfig
from cumulusci.core.config.org_config import OrgConfig
from cumulusci.core.config.scratch_org_config import ScratchOrgConfig
from cumulusci.tasks.vlocity.exceptions import BuildToolMissingError
from cumulusci.tasks.vlocity.vlocity import (
    BUILD_TOOL_MISSING_ERROR,
    VlocityDeployTask,
    VlocityRetrieveTask,
)


def test_vlocity_build_tool_missing(project_config):
    username = "foo"
    org_name = "dev"
    org_config = ScratchOrgConfig(
        {
            "instance_url": "https://test.salesforce.com",
            "username": username,
            "org_id": "00Dxxxxxxxxxxxx",
            "password": "test",
        },
        org_name,
        keychain=mock.Mock(),
    )
    task_config = TaskConfig(
        config={"options": {"job_file": "vlocity.yaml", "org": org_name}}
    )
    task = VlocityRetrieveTask(project_config, task_config, org_config)

    with mock.patch(
        "cumulusci.tasks.vlocity.vlocity.sarge.Command", mock.Mock({"returncode": 1})
    ):
        with pytest.raises(BuildToolMissingError, match=BUILD_TOOL_MISSING_ERROR):
            task._init_task()


username = "foo"
org_name = "dev"
access_token = "foo.bar.baz"
instance_url = "https://something.custom.salesforce.com"
scratch_org_config = ScratchOrgConfig(
    {
        "instance_url": "https://test.salesforce.com",
        "username": username,
        "org_id": "00Dxxxxxxxxxxxx",
        "password": "test",
    },
    org_name,
    keychain=mock.Mock(),
)
persistent_org_config = OrgConfig(
    {
        "instance_url": instance_url,
        "username": username,
        "org_id": "00Dxxxxxxxxxxxx",
        "access_token": access_token,
    },
    org_name,
    keychain=mock.Mock(),
)
vlocity_test_cases = [
    (
        scratch_org_config,
        VlocityRetrieveTask,
        f"vlocity packExport -job vlocity.yaml -sfdx.username '{username}'",
    ),
    (
        persistent_org_config,
        VlocityRetrieveTask,
        f"vlocity packExport -job vlocity.yaml -sf.accesstoken '{access_token}' -sf.instanceUrl '{instance_url}'",
    ),
    (
        scratch_org_config,
        VlocityDeployTask,
        f"vlocity packDeploy -job vlocity.yaml -sfdx.username '{username}'",
    ),
    (
        persistent_org_config,
        VlocityDeployTask,
        f"vlocity packDeploy -job vlocity.yaml -sf.accesstoken '{access_token}' -sf.instanceUrl '{instance_url}'",
    ),
]


@pytest.mark.parametrize("org_config,task_class,expected_command", vlocity_test_cases)
def test_vlocity_simple_job(project_config, org_config, task_class, expected_command):

    task_config = TaskConfig(
        config={"options": {"job_file": "vlocity.yaml", "org": org_name}}
    )
    task = task_class(project_config, task_config, org_config)

    assert task._get_command() == expected_command

from unittest import mock

import pytest

from cumulusci.core.config import TaskConfig
from cumulusci.core.config.org_config import OrgConfig
from cumulusci.core.config.scratch_org_config import ScratchOrgConfig
from cumulusci.tasks.vlocity.exceptions import BuildToolMissingError
from cumulusci.tasks.vlocity.vlocity import (
    BUILD_TOOL_MISSING_ERROR,
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


def test_vlocity_retrieve__scratch(project_config):
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

    assert (
        task._get_command()
        == f"vlocity packExport -job vlocity.yaml -sfdx.username '{username}'"
    )


def test_vlocity_retrieve__persistent(project_config):
    username = "foo"
    org_name = "dev"
    access_token = "foo.bar.baz"
    instance_url = "https://something.custom.salesforce.com"
    org_config = OrgConfig(
        {
            "instance_url": instance_url,
            "username": username,
            "org_id": "00Dxxxxxxxxxxxx",
            "access_token": access_token,
        },
        org_name,
        keychain=mock.Mock(),
    )
    task_config = TaskConfig(
        config={"options": {"job_file": "vlocity.yaml", "org": org_name}}
    )
    task = VlocityRetrieveTask(project_config, task_config, org_config)

    assert (
        task._get_command()
        == f"vlocity packExport -job vlocity.yaml -sf.accesstoken '{access_token}' -sf.instanceUrl '{instance_url}'"
    )


def test_vlocity_deploy__scratch(project_config):
    pass


def test_vlocity_deploy__persistent(project_config):
    pass

from unittest import mock

import pytest

from cumulusci.core.config import TaskConfig
from cumulusci.core.config.org_config import OrgConfig
from cumulusci.core.config.scratch_org_config import ScratchOrgConfig
from cumulusci.core.exceptions import CommandException
from cumulusci.core.utils import import_global
from cumulusci.tasks.vlocity.exceptions import BuildToolMissingError
from cumulusci.tasks.vlocity.vlocity import (
    BUILD_TOOL_MISSING_ERROR,
    LWC_RSS_NAME,
    OMNI_NAMESPACE,
    VF_LEGACY_RSS_NAME,
    VF_RSS_NAME,
    OmniStudioDeployRemoteSiteSettings,
    VlocityDeployTask,
    VlocityRetrieveTask,
)

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
        None,
        f"vlocity packExport -job vlocity.yaml -sfdx.username '{username}'",
    ),
    (
        persistent_org_config,
        VlocityRetrieveTask,
        None,
        f"vlocity packExport -job vlocity.yaml -sf.accessToken '{access_token}' -sf.instanceUrl '{instance_url}'",
    ),
    (
        scratch_org_config,
        VlocityDeployTask,
        None,
        f"vlocity packDeploy -job vlocity.yaml -sfdx.username '{username}'",
    ),
    (
        persistent_org_config,
        VlocityDeployTask,
        None,
        f"vlocity packDeploy -job vlocity.yaml -sf.accessToken '{access_token}' -sf.instanceUrl '{instance_url}'",
    ),
    (
        persistent_org_config,
        VlocityDeployTask,
        "foo=bar",
        f"vlocity packDeploy -job vlocity.yaml -sf.accessToken '{access_token}' -sf.instanceUrl '{instance_url}' foo=bar",
    ),
]


@pytest.mark.parametrize(
    "org_config,task_class,extra,expected_command", vlocity_test_cases
)
def test_vlocity_simple_job(
    project_config, org_config, task_class, extra, expected_command
):

    task_config = TaskConfig(
        config={
            "options": {"job_file": "vlocity.yaml", "org": org_name, "extra": extra}
        }
    )
    task = task_class(project_config, task_config, org_config)

    assert task._get_command() == expected_command


def test_vlocity_build_tool_missing(project_config):
    task_config = TaskConfig(
        config={"options": {"job_file": "vlocity.yaml", "org": org_name}}
    )
    task = VlocityRetrieveTask(project_config, task_config, scratch_org_config)

    with mock.patch(
        "cumulusci.tasks.vlocity.vlocity.sarge.Command",
        mock.Mock(side_effect=ValueError),
    ):
        with pytest.raises(BuildToolMissingError, match=BUILD_TOOL_MISSING_ERROR):
            task._init_task()


namespace = "cci"
test_cases = [
    (TaskConfig(config={}), OMNI_NAMESPACE),
    (TaskConfig(config={"options": {"namespace": namespace}}), namespace),
]


@pytest.mark.parametrize("task_config,expected_namespace", test_cases)
def test_deploy_omni_studio_site_settings(
    project_config, task_config, expected_namespace
):
    org_config = mock.Mock(
        installed_packages=[],
        instance_url="https://inspiration-velocity-34802-dev-ed.my.salesforce.com/",
        instance_name="CS28",
    )

    task = OmniStudioDeployRemoteSiteSettings(project_config, task_config, org_config)
    rss_options = task._get_options()
    records = rss_options.records

    expected_site_names = set([VF_RSS_NAME, VF_LEGACY_RSS_NAME, LWC_RSS_NAME])
    actual_site_names = set([r.full_name for r in records])
    assert expected_site_names == actual_site_names

    # when no 'namespace' option is specified, we default to the omni studio namespace
    expected_urls = set(
        [
            "https://inspiration-velocity-34802-dev-ed.lightning.force.com/",
            f"https://inspiration-velocity-34802-dev-ed--{expected_namespace}.vf.force.com/",
            f"https://inspiration-velocity-34802-dev-ed--{expected_namespace}.CS28.visual.force.com/",
        ]
    )
    actual_urls = set([r.url for r in records])
    assert expected_urls == actual_urls


# Run these tests with a command like:
# $ cci flow run omni:install_omnistudio --org omni
# $ pytest --org omni --run-slow-tests -k VlocityIntegration cumulusci/tasks/vlocity/tests/test_vlocity.py --opt-in

# Note that these tests are not totally reliable but I
# ran out of time. Worse comes to worse, run the same code at
# the CLI:
#
# $ cci task run omni:test_success --org omni
# $ cci task run omni:test_failure --org omni
#
# Finishing this code requires investigation into why SFDX cannot
# always find its orgs. Perhaps relating to cwd/env that the program.
#
# The frequent error is:
#
#     "name": "NoOrgFound",
#     "action": "Run the \"sfdx force:auth\" commands with --setdefaultusername to connect to an org and set it as your default org.\nRun \"force:org:create\" with --setdefaultusername to create a scratch org and set it as your default org.\nRun \"sfdx force:config:set defaultusername=<username>\" to set your default username."
# }


@pytest.mark.needs_org()
@pytest.mark.slow()
@pytest.mark.org_shape("omni", "omni:install_omnistudio")  # SUPER-SLOW!!!!
@pytest.mark.opt_in()  # this test probably does not work in CI yet due to dependence on omni-cci
class TestVlocityIntegration:
    def test_vlocity_integration(self, project_config, create_task, caplog):
        task_config = project_config.get_task("omni:test_success")
        task_class = import_global(task_config.class_path)
        task = create_task(
            task_class, task_config.options, project_config=task_config.project_config
        )
        try:
            task()
            assert task.return_values["returncode"] == 0
        except Exception:
            print(caplog.records)
            raise

    def test_vlocity_integration__error_handling(self, project_config, create_task):
        task_config = project_config.get_task("omni:test_failure")
        task_class = import_global(task_config.class_path)
        task = create_task(
            task_class, task_config.options, project_config=task_config.project_config
        )
        with pytest.raises(CommandException):
            task()

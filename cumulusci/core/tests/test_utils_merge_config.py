import copy

import pytest

from cumulusci.core import utils
from cumulusci.core.exceptions import ConfigMergeError


@pytest.fixture
def universal_config():
    return {
        "flows": {
            "steps_all_flows": {
                "group": "flowy",
                "description": "Elaborate description",
                "steps": {
                    1: {"flow": "short_flow", "options": {"foo": "bar"}},
                    2: {"flow": "mediuem_flow", "options": {"baz": "boop"}},
                    3: {"flow": "long_flow", "options": {"bim": "bap"}},
                },
            },
            "steps_all_tasks": {
                "group": "tasky",
                "description": "Elaborate description",
                "steps": {
                    1: {"task": "short_task", "options": {"foo": "bar"}},
                    2: {"task": "mediuem_task", "options": {"baz": "boop"}},
                    3: {"task": "long_task", "options": {"bim": "bap"}},
                },
            },
        }
    }


def test_init():
    config = utils.merge_config(
        {
            "universal_config": {"hello": "world"},
            "user_config": {"hello": "christian"},
        }
    )
    assert config["hello"] == "christian"


def test_merge_failure():
    with pytest.raises(ConfigMergeError) as cm:
        utils.merge_config(
            {
                "universal_config": {"hello": "world", "test": {"sample": 1}},
                "user_config": {"hello": "christian", "test": [1, 2]},
            }
        )
    exception = cm.value
    assert exception.config_name == "user_config"


def test_cleanup_flow_step_override_conflicts__no_op(universal_config):
    configs = {"universal_config": universal_config}
    clean_configs = utils.cleanup_flow_step_override_conflicts(configs)
    assert universal_config == clean_configs["universal_config"]


def test_cleanup_flow_step_override_conflicts__task_overrides_flow(universal_config):
    project_config = {
        "flows": {
            "steps_all_flows": {
                "steps": {3: {"task": "custom_task", "options": {"super": "cool"}}}
            }
        }
    }
    configs = {"project_config": project_config, "universal_config": universal_config}
    clean_configs = utils.cleanup_flow_step_override_conflicts(configs)

    expected_universal_config = copy.deepcopy(universal_config)
    expected_universal_config["flows"]["steps_all_flows"]["steps"][3] = {}
    assert expected_universal_config == clean_configs["universal_config"]


def test_cleanup_flow_step_override_conflicts__flow_overrides_task(universal_config):
    project_config = {
        "flows": {
            "steps_all_tasks": {
                "steps": {3: {"flow": "custom_task", "options": {"super": "cool"}}}
            }
        }
    }
    configs = {"project_config": project_config, "universal_config": universal_config}
    clean_configs = utils.cleanup_flow_step_override_conflicts(configs)

    expected_universal_config = copy.deepcopy(universal_config)
    expected_universal_config["flows"]["steps_all_tasks"]["steps"][3] = {}

    assert expected_universal_config == clean_configs["universal_config"]


def test_cleanup_flow_step_override_conflicts__multiple_overrides_of_alternating_types(
    universal_config,
):
    """This is to simulate a rare but plausible case where an user has multiple overrides of the same flow step
    accross three different config objects: global, project, and project_local.

    The result should be that any flow steps with differing types will be set to an empty dict, as
    was tested above. We also expect that any steps of the same type will _not_ be set to an empty dict.
    (Steps of the same type will override each other when dictmerge() is called)
    """
    project_local_config = {
        "flows": {
            "steps_all_tasks": {
                "steps": {3: {"flow": "custom_flow_one", "options": {"Trog": "dor"}}}
            }
        }
    }
    project_config = {
        "flows": {
            "steps_all_tasks": {
                "steps": {3: {"task": "custom_task", "options": {"deploy": "clippy"}}}
            }
        }
    }
    global_config = {
        "flows": {
            "steps_all_tasks": {
                "steps": {3: {"flow": "custom_flow_two", "options": {"Just": "do it"}}}
            }
        }
    }

    configs = {
        "global_config": global_config,
        "project_config": project_config,
        "project_local_config": project_local_config,
        "universal_config": universal_config,
    }

    clean_configs = utils.cleanup_flow_step_override_conflicts(configs)

    expected_universal_config = copy.deepcopy(universal_config)
    expected_universal_config["flows"]["steps_all_tasks"]["steps"][3] = {}

    expected_project_config = copy.deepcopy(project_config)
    expected_project_config["flows"]["steps_all_tasks"]["steps"][3] = {}

    assert expected_universal_config == clean_configs["universal_config"]
    assert expected_project_config == clean_configs["project_config"]
    # These should remain unchanged
    assert project_local_config == clean_configs["project_local_config"]
    assert global_config == clean_configs["global_config"]

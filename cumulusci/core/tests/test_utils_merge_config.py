import copy

import pytest

from cumulusci.core import utils
from cumulusci.core.exceptions import ConfigMergeError, CumulusCIException


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
    with pytest.raises(ConfigMergeError) as e:
        utils.merge_config(
            {
                "universal_config": {"hello": "world", "test": {"sample": 1}},
                "user_config": {"hello": "christian", "test": [1, 2]},
            }
        )
    exception = e.value
    assert exception.config_name == "user_config"


def test_cleanup_flow_step_override_conflicts__no_op(universal_config):
    configs = {"universal_config": universal_config}
    clean_configs = utils.cleanup_flow_step_override_conflicts(configs)
    assert universal_config == clean_configs["universal_config"]


def test_cleanup_flow_step_override_conflicts__ambiguous_step(universal_config):
    project_config = {
        "flows": {"steps_all_flows": {"steps": {3: {"flow": "None", "task": "None"}}}}
    }

    configs = {"project_config": project_config, "universal_config": universal_config}
    with pytest.raises(CumulusCIException):
        utils.cleanup_flow_step_override_conflicts(configs)


def test_cleanup_flow_step_override_conflicts__task_overrides_flow(universal_config):
    project_config = {
        "flows": {
            "steps_all_flows": {
                "steps": {3: {"task": "custom_task", "options": {"super": "cool"}}}
            }
        }
    }
    # Copy things before they're operated on
    expected_universal_config = copy.deepcopy(universal_config)
    expected_universal_config["flows"]["steps_all_flows"]["steps"][3] = {}

    configs = {"project_config": project_config, "universal_config": universal_config}
    clean_configs = utils.cleanup_flow_step_override_conflicts(configs)

    assert expected_universal_config == clean_configs["universal_config"]


def test_cleanup_flow_step_override_conflicts__flow_overrides_task(universal_config):
    project_config = {
        "flows": {
            "steps_all_tasks": {
                "steps": {3: {"flow": "custom_task", "options": {"super": "cool"}}}
            }
        }
    }
    # Copy things before they're operated on
    expected_universal_config = copy.deepcopy(universal_config)
    expected_universal_config["flows"]["steps_all_tasks"]["steps"][3] = {}

    configs = {"project_config": project_config, "universal_config": universal_config}
    clean_configs = utils.cleanup_flow_step_override_conflicts(configs)

    assert expected_universal_config == clean_configs["universal_config"]


def test_cleanup_flow_step_override__old_syntax_task_to_flow(universal_config):
    """The 'old' syntax was to set the current step type to 'None' and the new
    step type with the name of the task/flow you want."""
    project_config = {
        "flows": {
            "steps_all_tasks": {
                "steps": {
                    3: {
                        "task": "None",
                        "flow": "custom_task",
                        "options": {"super": "cool"},
                    }
                }
            }
        }
    }
    # Copy things before they're operated on
    expected_project_config = copy.deepcopy(project_config)
    expected_project_config["flows"]["steps_all_tasks"]["steps"][3] = {
        # "task" should no longer be present
        "flow": "custom_task",
        "options": {"super": "cool"},
    }

    configs = {"project_config": project_config, "universal_config": universal_config}
    clean_configs = utils.cleanup_flow_step_override_conflicts(configs)

    assert expected_project_config == clean_configs["project_config"]


def test_cleanup_flow_step_override__old_syntax_flow_to_task(universal_config):
    """The 'old' syntax was to set the current step type to 'None' and the new
    step type with the name of the task/flow you want."""
    project_config = {
        "flows": {
            "steps_all_flows": {
                "steps": {
                    3: {
                        "flow": "None",
                        "task": "custom_task",
                        "options": {"super": "cool"},
                    }
                }
            }
        }
    }
    # Copy things before they're operated on
    expected_project_config = copy.deepcopy(project_config)
    expected_project_config["flows"]["steps_all_flows"]["steps"][3] = {
        # "task" should no longer be present
        "task": "custom_task",
        "options": {"super": "cool"},
    }

    configs = {"project_config": project_config, "universal_config": universal_config}
    clean_configs = utils.cleanup_flow_step_override_conflicts(configs)

    assert expected_project_config == clean_configs["project_config"]


def test_cleanup_flow_step_override_conflicts__multiple_overrides_of_alternating_types(
    universal_config,
):
    """This is to simulate a rare but plausible case where an user has multiple overrides of the same flow step
    accross three different config objects: global, project, and project_local.

    The result should be that any flow steps with differing types will be set to an empty dict, as
    was tested above. We also expect that any steps of the same type will _not_ be set to an empty dict.
    (Steps of the same type will override each other when dictmerge() is called)
    """
    # Throw in the old replace syntax just for fun
    project_local_config = {
        "flows": {
            "steps_all_tasks": {
                "steps": {
                    3: {
                        "task": "None",
                        "flow": "custom_flow_one",
                        "options": {"Trog": "dor"},
                    }
                }
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
    # Even throwing in the old replace syntax just for fun
    global_config = {
        "flows": {
            "steps_all_tasks": {
                "steps": {
                    3: {
                        "flow": "custom_flow_two",
                        "options": {"Just": "do it"},
                    }
                }
            }
        }
    }

    # Copy things before they are operated on
    expected_universal_config = copy.deepcopy(universal_config)
    expected_universal_config["flows"]["steps_all_tasks"]["steps"][3] = {}

    expected_project_config = copy.deepcopy(project_config)
    expected_project_config["flows"]["steps_all_tasks"]["steps"][3] = {
        "flow": "custom_flow_two"
    }

    expected_project_local_config = copy.deepcopy(project_local_config)
    expected_project_local_config["flows"]["steps_all_tasks"]["steps"][3] = {
        "flow": "custom_flow_one",
        "options": {"Trog": "dor"},
    }

    expected_global_config = copy.deepcopy(global_config)

    configs = {
        "global_config": global_config,
        "project_config": project_config,
        "project_local_config": project_local_config,
        "universal_config": universal_config,
    }
    clean_configs = utils.cleanup_flow_step_override_conflicts(configs)

    assert expected_universal_config == clean_configs["universal_config"]
    assert expected_project_config == clean_configs["project_config"]
    assert expected_project_local_config == clean_configs["project_local_config"]
    # This should remain unchanged
    assert expected_global_config == clean_configs["global_config"]


def test_cleanup_flow_step_override_conflicts__obsolete_flow_with_tasks(
    universal_config,
):
    project_config = {
        "flows": {"steps_all_tasks": {"tasks": {1: {"task": "custom_task"}}}}
    }

    expected_project_config = copy.deepcopy(project_config)
    expected_project_config["flows"]["steps_all_tasks"]["tasks"] = {
        1: {"task": "custom_task"}
    }

    configs = {
        "project_config": project_config,
        "universal_config": universal_config,
    }
    clean_configs = utils.cleanup_flow_step_override_conflicts(configs)

    assert expected_project_config == clean_configs["project_config"]


def test_link_missing_task_or_flow():
    step_config_to_override = {"task": "util_sleep"}
    overriding_step_config = {"options": {"seconds": 1}}

    assert "task" not in overriding_step_config
    utils.link_missing_task_or_flow(step_config_to_override, overriding_step_config)
    assert overriding_step_config == {
        "task": "util_sleep",
        "options": {"seconds": 1},
    }

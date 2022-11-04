import logging
from unittest import mock

import pytest

import cumulusci
from cumulusci.core.config import FlowConfig, OrgConfig
from cumulusci.core.exceptions import (
    FlowConfigError,
    FlowInfiniteLoopError,
    TaskNotFoundError,
)
from cumulusci.core.flowrunner import (
    FlowCoordinator,
    PreflightFlowCoordinator,
    StepSpec,
    TaskRunner,
)
from cumulusci.core.tasks import BaseTask
from cumulusci.core.tests.utils import MockLoggingHandler
from cumulusci.tests.util import create_project_config

ORG_ID = "00D000000000001"


class _TaskReturnsStuff(BaseTask):
    def _run_task(self):
        self.return_values = {"name": "supername"}


class _TaskResponseName(BaseTask):
    task_options = {"response": {"description": "the response to print"}}

    def _run_task(self):
        return self.options["response"]


class _TaskRaisesException(BaseTask):
    task_options = {
        "exception": {"description": "The exception to raise"},
        "message": {"description": "The exception message"},
    }

    def _run_task(self):
        raise self.options["exception"](self.options["message"])


class _SfdcTask(BaseTask):
    salesforce_task = True

    def _run_task(self):
        return -1


class AbstractFlowCoordinatorTest:
    @classmethod
    def setup_class(cls):
        logger = logging.getLogger(cumulusci.__name__)
        logger.setLevel(logging.DEBUG)
        cls._flow_log_handler = MockLoggingHandler(logging.DEBUG)
        logger.addHandler(cls._flow_log_handler)

    def setup_method(self):
        self.project_config = create_project_config("TestOwner", "TestRepo")
        self.org_config = OrgConfig(
            {"username": "sample@example", "org_id": ORG_ID}, "test", mock.Mock()
        )
        self.org_config.refresh_oauth_token = mock.Mock()

        self._flow_log_handler.reset()
        self.flow_log = self._flow_log_handler.messages
        self._setup_project_config()

    def _setup_project_config(self):
        pass


class TestFullParseTestFlowCoordinator(AbstractFlowCoordinatorTest):
    def test_each_flow(self):
        for flow_name in [
            flow_info["name"] for flow_info in self.project_config.list_flows()
        ]:
            try:
                flow_config = self.project_config.get_flow(flow_name)
                flow = FlowCoordinator(self.project_config, flow_config, name=flow_name)
            except Exception as exc:
                self.fail(f"Error creating flow {flow_name}: {str(exc)}")
            assert flow.steps is not None, f"Flow {flow_name} parsed to no steps"
            print(f"Parsed flow {flow_name} as {len(flow.steps)} steps")


class TestSimpleTestFlowCoordinator(AbstractFlowCoordinatorTest):
    """Tests the expectations of a BaseFlow caller"""

    def _setup_project_config(self):
        self.project_config.config["tasks"] = {
            "pass_name": {
                "description": "Pass the name",
                "class_path": "cumulusci.core.tests.test_flowrunner._TaskReturnsStuff",
            },
            "name_response": {
                "description": "Pass the name",
                "class_path": "cumulusci.core.tests.test_flowrunner._TaskResponseName",
            },
            "raise_exception": {
                "description": "Raises an exception",
                "class_path": "cumulusci.core.tests.test_flowrunner._TaskRaisesException",
                "options": {
                    "exception": Exception,
                    "message": "Test raised exception as expected",
                },
            },
            "sfdc_task": {
                "description": "An sfdc task",
                "class_path": "cumulusci.core.tests.test_flowrunner._SfdcTask",
            },
        }
        self.project_config.config["flows"] = {
            "nested_flow": {
                "description": "A flow that runs inside another flow",
                "steps": {1: {"task": "pass_name"}},
            },
            "nested_flow_2": {
                "description": "A flow that runs inside another flow, and calls another flow",
                "steps": {1: {"task": "pass_name"}, 2: {"flow": "nested_flow"}},
            },
        }

    def test_init(self):
        flow_config = FlowConfig({"steps": {"1": {"task": "pass_name"}}})
        flow = FlowCoordinator(self.project_config, flow_config, name="test_flow")

        assert len(flow.steps) == 1
        assert hasattr(flow, "logger") is True

    def test_step_sorting(self):
        self.project_config.config["flows"] = {
            "test": {"steps": {"1": {"flow": "subflow"}, "1.1": {"task": "pass_name"}}},
            "subflow": {"steps": {"1": {"task": "pass_name"}}},
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config, name="test_flow")
        assert [str(step.step_num) for step in flow.steps] == ["1/1", "1.1"]

    def test_get_summary(self):
        self.project_config.config["flows"]["test"] = {
            "description": "test description",
            "steps": {"1": {"flow": "nested_flow_2"}},
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config, name="test_flow")
        actual_output = flow.get_summary()
        expected_output = (
            "Description: test description"
            + "\n\nFlow Steps"
            + "\n1) flow: nested_flow_2 [from current folder]"
            + "\n    1) task: pass_name"
            + "\n    2) flow: nested_flow"
            + "\n        1) task: pass_name"
        )
        assert expected_output == actual_output

    def test_get_flow_steps(self):
        self.project_config.config["flows"]["test"] = {
            "description": "test description",
            "steps": {"1": {"flow": "nested_flow_2"}},
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config, name="test_flow")
        actual_output = flow.get_flow_steps()
        expected_output = [
            "1) flow: nested_flow_2 [from current folder]",
            "    1) task: pass_name",
            "    2) flow: nested_flow",
            "        1) task: pass_name",
        ]
        assert expected_output == actual_output

    def test_get_flow_steps__for_docs(self):
        self.project_config.config["flows"]["test"] = {
            "description": "test description",
            "steps": {"1": {"flow": "nested_flow_2"}},
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config, name="test_flow")
        actual_output = flow.get_flow_steps(for_docs=True)
        expected_output = [
            "1) flow: nested_flow_2",
            "    1) task: pass_name",
            "    2) flow: nested_flow",
            "        1) task: pass_name",
        ]
        assert expected_output == actual_output

    def test_get_flow_steps__verbose(self):
        self.project_config.config["flows"]["test"] = {
            "description": "test description",
            "steps": {
                "1": {
                    "task": "pass_name",
                    "options": {"option_name": "option_value"},
                }
            },
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config, name="test_flow")
        actual_output = flow.get_flow_steps(verbose=True)
        expected_output = [
            "1) task: pass_name [from current folder]",
            "   options:\n       option_name: option_value",
        ]
        assert expected_output == actual_output

    def test_get_summary__substeps(self):
        flow = FlowCoordinator.from_steps(
            self.project_config,
            [StepSpec("1", "test", {}, None, self.project_config, from_flow="test")],
        )
        assert flow.get_summary() == ""

    def test_get_summary__multiple_sources(self):
        other_project_config = mock.MagicMock()
        other_project_config.source.__str__.return_value = "other source"
        flow = FlowCoordinator.from_steps(
            self.project_config,
            [
                StepSpec(
                    "1/1",
                    "other:test1",
                    {},
                    None,
                    other_project_config,
                    from_flow="test",
                ),
                StepSpec(
                    "1/2", "test2", {}, None, self.project_config, from_flow="test"
                ),
            ],
        )
        actual_output = flow.get_summary()
        assert (
            "\nFlow Steps"
            + "\n1) flow: test"
            + "\n    1) task: other:test1 [from other source]"
            + "\n    2) task: test2 [from current folder]"
        ) == actual_output

    def test_init__options(self):
        """A flow can accept task options and pass them to the task."""

        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "name_response", "options": {"response": "foo"}}},
            }
        )

        flow = FlowCoordinator(
            self.project_config,
            flow_config,
            options={"name_response": {"response": "bar"}},
        )

        # the first step should have the option
        assert flow.steps[0].task_config["options"]["response"] == "bar"

    def test_init__nested_options(self):
        self.project_config.config["flows"]["test"] = {
            "description": "Run a flow with task options",
            "steps": {
                1: {"flow": "nested_flow", "options": {"pass_name": {"foo": "bar"}}}
            },
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config)
        assert flow.steps[0].task_config["options"]["foo"] == "bar"

    def test_init__bad_classpath(self):
        self.project_config.config["tasks"] = {
            "classless": {
                "description": "Bogus class_path",
                "class_path": "this.is.not.a.thing",
            }
        }
        flow_config = FlowConfig(
            {
                "description": "A flow with a broken task",
                "steps": {1: {"task": "classless"}},
            }
        )
        with pytest.raises(FlowConfigError):
            FlowCoordinator(self.project_config, flow_config, name="test")

    def test_init__task_not_found(self):
        """A flow with reference to a task that doesn't exist in the
        project will throw a TaskNotFoundError"""

        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "pass_name"}, 2: {"task": "do_delightulthings"}},
            }
        )
        with pytest.raises(TaskNotFoundError):
            FlowCoordinator(self.project_config, flow_config)

    def test_init__no_steps_in_config(self):
        flow_config = FlowConfig({})
        with pytest.raises(FlowConfigError):
            FlowCoordinator(self.project_config, flow_config, name="test")

    def test_init_old_format(self):
        flow_config = FlowConfig({"tasks": {}})
        with pytest.raises(FlowConfigError):
            FlowCoordinator(self.project_config, flow_config, name="test")

    def test_init_recursive_flow(self):
        self.project_config.config["flows"] = {
            "self_referential_flow": {
                "description": "A flow that runs inside another flow",
                "steps": {1: {"flow": "self_referential_flow"}},
            }
        }
        flow_config = self.project_config.get_flow("self_referential_flow")
        with pytest.raises(FlowInfiniteLoopError):
            FlowCoordinator(
                self.project_config, flow_config, name="self_referential_flow"
            )

    def test_init_flow__with_infinite_loop(self):
        """Test a more complicated flow tree with recursion"""
        self.project_config.config["flows"] = {
            "grandchild_flow": {
                "description": "A flow that runs inside another flow",
                "steps": {1: {"task": "pass_name"}},
            },
            "parent_flow": {
                "description": "A flow that calls another flow",
                "steps": {
                    1: {"flow": "grandchild_flow"},
                    2: {"task": "pass_name"},
                    3: {"flow": "grandchild_flow"},
                },
            },
            "grandparent_flow": {
                "description": "A flow that calls another flow",
                "steps": {
                    1: {"flow": "grandchild_flow"},
                    2: {"flow": "parent_flow"},
                    3: {"task": "pass_name"},
                    5: {"flow": "recursive_flow"},
                },
            },
            "recursive_flow": {
                "description": "A flow that calls grandparent flow adding recursion",
                "steps": {
                    1: {"flow": "grandchild_flow"},
                    2: {"flow": "grandparent_flow"},
                },
            },
        }
        flow_config = self.project_config.get_flow("grandparent_flow")
        with pytest.raises(FlowInfiniteLoopError):
            FlowCoordinator(self.project_config, flow_config, name="grandparent_flow")

    def test_init_flow__without_infinite_loop(self):
        """It's OK if a flow is called multiple times if not recursive"""
        self.project_config.config["flows"] = {
            "grandchild_flow": {
                "description": "A flow that runs inside another flow",
                "steps": {1: {"task": "pass_name"}},
            },
            "parent_flow": {
                "description": "A flow that calls another flow",
                "steps": {
                    1: {"flow": "grandchild_flow"},
                    2: {"task": "pass_name"},
                    3: {"flow": "grandchild_flow"},
                },
            },
            "grandparent_flow": {
                "description": "A flow that calls another flow",
                "steps": {
                    1: {"flow": "parent_flow"},
                    2: {"flow": "grandchild_flow"},
                    3: {"task": "pass_name"},
                    4: {"task": "pass_name"},
                },
            },
        }
        flow_config = self.project_config.get_flow("grandparent_flow")
        FlowCoordinator(self.project_config, flow_config, name="grandparent_flow")

    def test_from_steps(self):
        steps = [StepSpec("1", "test", {}, _TaskReturnsStuff, None)]
        flow = FlowCoordinator.from_steps(self.project_config, steps)
        assert 1 == len(flow.steps)

    def test_run__one_task(self):
        """A flow with one task will execute the task"""
        flow_config = FlowConfig(
            {"description": "Run one task", "steps": {1: {"task": "pass_name"}}}
        )
        flow = FlowCoordinator(self.project_config, flow_config)
        assert 1 == len(flow.steps)

        flow.run(self.org_config)

        assert any(flow_config.description in s for s in self.flow_log["info"])
        assert {"name": "supername"} == flow.results[0].return_values

    def test_run__nested_flow(self):
        """Flows can run inside other flows"""
        self.project_config.config["flows"]["test"] = {
            "description": "Run a task and a flow",
            "steps": {1: {"task": "pass_name"}, 2: {"flow": "nested_flow"}},
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)
        assert 2 == len(flow.steps)
        assert flow.results[0].return_values == flow.results[1].return_values

    def test_run__nested_flow_2(self):
        """Flows can run inside other flows and call other flows"""
        self.project_config.config["flows"]["test"] = {
            "description": "Run a task and a flow",
            "steps": {1: {"task": "pass_name"}, 2: {"flow": "nested_flow_2"}},
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)
        assert 3 == len(flow.steps)
        assert flow.results[0].return_values == flow.results[1].return_values
        assert flow.results[1].return_values == flow.results[2].return_values

    def test_run__option_backrefs(self):
        """A flow's options reach into return values from other tasks."""

        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {
                    1: {"task": "pass_name"},
                    2: {
                        "task": "name_response",
                        "options": {"response": "^^pass_name.name"},
                    },
                },
            }
        )

        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)
        # the flow results for the second task should be 'name'
        assert flow.results[1].result == "supername"

    def test_run__option_backref_not_found(self):
        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {
                    1: {"task": "pass_name"},
                    2: {
                        "task": "name_response",
                        "options": {"response": "^^bogus.name"},
                    },
                },
            }
        )

        flow = FlowCoordinator(self.project_config, flow_config)
        with pytest.raises(NameError):
            flow.run(self.org_config)

    def test_run__nested_option_backrefs(self):
        self.project_config.config["flows"]["test"] = {
            "description": "Run two tasks",
            "steps": {
                1: {"flow": "nested_flow"},
                2: {
                    "task": "name_response",
                    "options": {"response": "^^nested_flow.pass_name.name"},
                },
            },
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)

        assert flow.results[-1].result == "supername"

    def test_run__skip_flow_None(self):
        flow_config = FlowConfig(
            {
                "description": "A flow that skips its only step",
                "steps": {1: {"task": "None"}},
            }
        )
        callbacks = mock.Mock()
        flow = FlowCoordinator(
            self.project_config, flow_config, name="skip", callbacks=callbacks
        )
        flow.run(self.org_config)
        callbacks.pre_task.assert_not_called()

    def test_run__skip_from_init(self):
        """A flow can receive during init a list of tasks to skip"""

        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {
                    1: {"task": "pass_name"},
                    2: {
                        "task": "name_response",
                        "options": {"response": "^^pass_name.name"},
                    },
                },
            }
        )
        flow = FlowCoordinator(self.project_config, flow_config, skip=["name_response"])
        flow.run(self.org_config)

        # the number of results should be 1 instead of 2
        assert 1 == len(flow.results)

    def test_run__skip_conditional_step(self):
        flow_config = FlowConfig({"steps": {1: {"task": "pass_name", "when": "False"}}})
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)
        assert len(flow.results) == 0

    def test_run__task_raises_exception_fail(self):
        """A flow aborts when a task raises an exception"""

        flow_config = FlowConfig(
            {"description": "Run a task", "steps": {1: {"task": "raise_exception"}}}
        )
        flow = FlowCoordinator(self.project_config, flow_config)
        with pytest.raises(Exception):
            flow.run(self.org_config)

    def test_run__task_raises_exception_ignore(self):
        """A flow continues when a task configured with ignore_failure raises an exception"""

        flow_config = FlowConfig(
            {
                "description": "Run a task",
                "steps": {
                    1: {"task": "raise_exception", "ignore_failure": True},
                    2: {"task": "pass_name"},
                },
            }
        )
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)
        assert 2 == len(flow.results)
        assert flow.results[0].exception is not None

    def test_run__no_steps(self):
        """A flow with no tasks will have no results."""
        flow_config = FlowConfig({"description": "Run no tasks", "steps": {}})
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)

        assert [] == flow.steps
        assert [] == flow.results

    def test_run__prints_org_id(self):
        """A flow with an org prints the org ID"""

        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "pass_name"}, 2: {"task": "sfdc_task"}},
            }
        )
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)

        org_id_logs = [s for s in self.flow_log["info"] if ORG_ID in s]

        assert 1 == len(org_id_logs)

    def test_init_org_updates_keychain(self):
        self.org_config.save = save = mock.Mock()

        def change_username(keychain):
            self.org_config.config["username"] = "sample2@example"

        self.org_config.refresh_oauth_token = change_username

        flow_config = FlowConfig({"steps": {1: {"task": "pass_name"}}})
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.org_config = self.org_config
        flow._init_org()

        save.assert_called_once()


class TestStepSpec:
    def test_repr(self):
        spec = StepSpec(1, "test_task", {}, None, None, skip=True)
        assert repr(spec) == "<!SKIP! StepSpec 1:test_task {}>"


class TestPreflightFlowCoordinatorTest(AbstractFlowCoordinatorTest):
    def test_run(self):
        flow_config = FlowConfig(
            {
                "checks": [
                    {"when": "True", "action": "error", "message": "Failed plan check"}
                ],
                "steps": {
                    1: {
                        "task": "log",
                        "options": {"level": "info", "line": "step"},
                        "checks": [
                            {
                                "when": "tasks.log(level='info', line='plan')",
                                "action": "error",
                                "message": "Failed step check 1",
                            },
                            {
                                "when": "not tasks.log(level='info', line='plan')",
                                "action": "error",
                                "message": "Failed step check 2",
                            },
                        ],
                    }
                },
            }
        )
        flow = PreflightFlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)

        assert {
            None: [{"status": "error", "message": "Failed plan check"}],
            "1": [{"status": "error", "message": "Failed step check 2"}],
        } == flow.preflight_results
        # Make sure task result got cached
        key = ("log", (("level", "info"), ("line", "plan")))
        assert key in flow._task_caches[flow.project_config].results

    def test_run__cross_project_preflights(self):
        other_project_config = mock.MagicMock()
        other_project_config.source.__str__.return_value = "other source"
        other_project_config.tasks = {
            "foo": {
                "class_path": "cumulusci.tasks.util.LogLine",
                "options": {"level": "info", "line": "test"},
            }
        }
        flow = PreflightFlowCoordinator.from_steps(
            self.project_config,
            [
                StepSpec(
                    "1/1",
                    "other:test1",
                    {
                        "checks": [{"when": "not tasks.foo()", "action": "error"}],
                    },
                    None,
                    other_project_config,
                    from_flow="test",
                ),
                StepSpec(
                    "1/2", "test2", {}, None, self.project_config, from_flow="test"
                ),
            ],
        )
        flow.run(self.org_config)
        key = ("foo", ())
        assert key in flow._task_caches[other_project_config].results
        # log doesn't return anything => None is falsy => preflight is True
        # which results in the action taking place (error)
        assert {
            "1/1": [{"status": "error", "message": None}],
        } == flow.preflight_results


@pytest.fixture
def task_runner():
    return TaskRunner(None, None)


@pytest.fixture
def task_options():
    return {"color": {"description": "It's a color!", "required": True}}


@pytest.fixture
def task_options_sensitive():
    return {
        "color": {"description": "It's a color!", "required": True, "sensitive": True}
    }


def test_log_options__no_task_options(task_runner):
    task = mock.Mock()
    task.task_options = None
    task_runner._log_options(task)

    task.logger.info.assert_called_once_with("No task options present")


def test_log_options__options_not_list(task_runner, task_options):
    task = mock.Mock()
    task.task_options = task_options
    task.options = {"color": "burgundy"}
    task_runner._log_options(task)

    task.logger.info.assert_called_with("  color: burgundy")


def test_log_options__options_not_list__sensitive(task_runner, task_options_sensitive):
    task = mock.Mock()
    task.task_options = task_options_sensitive
    task.options = {"color": "burgundy"}
    task_runner._log_options(task)

    task.logger.info.assert_called_with("  color: ********")


def test_log_options__options_is_list(task_runner, task_options):
    task = mock.Mock()
    task.task_options = task_options
    task.options = {"color": ["burgundy", "chartreuse", "turquoise"]}
    task_runner._log_options(task)

    task.logger.info.assert_any_call("  color:")
    task.logger.info.assert_any_call("    - burgundy")
    task.logger.info.assert_any_call("    - chartreuse")
    task.logger.info.assert_any_call("    - turquoise")


def test_log_options__options_is_list__sensitive(task_runner, task_options_sensitive):
    task = mock.Mock()
    task.task_options = task_options_sensitive
    task.options = {"color": ["burgundy", "chartreuse", "turquoise"]}
    task_runner._log_options(task)

    task.logger.info.assert_any_call("  color:")
    task.logger.info.assert_any_call("    - ********")

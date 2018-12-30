""" FlowRunner contains the logic for actually running a flow.

Flows are an integral part of CCI, they actually *do the thing*. We've been getting
along quite nicely with BaseFlow, which turns a flow definition into a callable
object that runs the flow in one fell swoop. We named it BaseFlow thinking that,
like tasks, specific flows might subclass it to extend behavior. In practice,
unlike BaseTask, subclasses ended up representing variations in how the flow
should actually be executed. We added callback hooks like pre_task and post_task
for host systems embedding cci, like web apps, to inspect the flow in progress.

BaseFlow suited us well.

FlowRunner is a v2 API for flows in CCI. There are two objects of interest:
- FlowCoordinator: takes a flow_config & runtime options to create a set of `StepSpec`s
- TaskRunner: encapsulates the actual task running, result providing logic.

Upon initialization, FlowRunner:
- Creates a logger
- Validates that there are no cycles in the given flow_config
- Validates that the flow_config is using new-style-steps
- Collects a list of StepSpec objects that define what the flow will do.

Upon running the flow, FlowRunner:
- Refreshes the org credentials
- Runs each StepSpec in order
- * Logs the task or skip
- * Updates any ^^ task option values with return_values references
- * handles any exceptions and sets return values

Option values/overrides can be passed in at a number of levels, in increasing order of priority:
- Task default (i.e. `.tasks.TASKNAME.options`)
- Flow definition task options (i.e. `.flows.FLOWNAME.steps.STEPNUM.options`)
- Flow definition subflow options (i.e. `.flows.FLOWNAME.steps.STEPNUM.options.TASKNAME`)
    see `dev_org_namespaced` for an example
- Flow runtime (i.e. on the commandline)


"""

# we don't actually use this set of imports, they're just in type
# comments, which require explicit runtime import when checking...
try:
    from typing import List
except ImportError:
    pass

import copy
import logging
import traceback
from collections import namedtuple
from distutils.version import LooseVersion

from cumulusci.core.exceptions import FlowConfigError, FlowInfiniteLoopError
from cumulusci.core.utils import import_class


class StepSpec(object):
    """ simple namespace to describe what the flowrunner should do each step """

    def __init__(
        self,
        step_num,
        task_name,
        task_options,
        allow_failure=False,
        from_flow=None,
        skip=None,
    ):
        self.step_num = step_num
        self.task_name = task_name
        self.task_options = task_options
        self.allow_failure = allow_failure
        self.from_flow = from_flow
        self.skip = skip

    def __repr__(self):
        skipstr = ""
        if self.skip:
            skipstr = "!SKIP! "
        return "<{skip}StepSpec {num}:{name} {cfg}>".format(
            num=self.step_num, name=self.task_name, cfg=self.task_options, skip=skipstr
        )


StepResult = namedtuple(
    "StepResult", ["step_num", "task_name", "result", "return_values", "exception"]
)


class TaskRunner(object):
    def __init__(self, project_config, org_config, runtime=None, raise_err=True):
        self.project_config = project_config  # TODO: Runtime only instead of PC?
        self.runtime = runtime
        self.org_config = org_config
        self.raise_err = raise_err

    def run_step(self, step):
        """
        Run a step.

        :param step: StepSpec
        :return: StepResult
        """
        # get task implementation class for task_name in step
        task_config = copy.deepcopy(self.project_config.get_task(step.task_name))
        task_class = import_class(task_config.class_path)

        # TODO: Actually override options based on step_config
        # TODO: Resolve ^^task_name.return_value style option syntax

        try:
            task = task_class(
                self.project_config,
                task_config,
                org_config=self.org_config,
                name=step.task_name,
                stepnum=step.step_num,
                flow=self,
            )
            task()
        except Exception as e:
            self.logger.exception("Exception in task {}".format(step.task_name))
            if self.raise_err:
                raise e
        finally:
            return StepResult(
                step.step_num, step.task_name, task.result, task.return_values
            )


class FlowCoordinator(object):
    def __init__(self, project_config, flow_config, options=None, skip=None):
        self.project_config = project_config
        self.flow_config = flow_config
        self.org_config = None

        # TODO: Support Runtime Options
        if not options:
            options = {}
        self.runtime_options = options

        if not skip:
            skip = []
        self.skip = skip

        self.results = []

        self.logger = self._init_logger()
        self.steps = self._init_steps()  # type: List[StepSpec]

    def _rule(self, fill="=", length=30):
        self.logger.info("{:{fill}<{length}}".format("", fill=fill, length=length))

    def run(self, org_config):
        self.org_config = org_config
        line = "Initializing flow: {}".format(self.__class__.__name__)
        if self.name:
            line = "{} ({})".format(line, self.name)
        self._rule()
        self.logger.info(line)
        self._rule()
        self.logger.info("")
        self._init_org()

        for step in self.steps:
            self._rule(fill="-")
            self.logger.into("Running task: {}".format(step.task_name))
            self._rule(fill="-")

            # TODO: Pass raise_err as !allow_failure
            runner = TaskRunner(self.project_config, org_config=org_config)
            result = runner.run_step(step)

            self.results.append(result)

    def _init_logger(self):
        """
        Returns a logger-like object to use for the duration of the flow.

        This could be a static in the base implementation, but subclasses may want to
        use instance details to log to the right place in the database.

        :return: logging.Logger
        """
        return logging.getLogger(__name__)

    def _init_steps(self,):
        """
        Given the flow config and everything else, create a list of steps to run.

        :return: List[StepSpec]
        """
        config_steps = self.flow_config.steps

        self._check_old_yaml_format()
        self._check_infinite_flows(config_steps)

        steps = []

        for number, step_config in config_steps.items():
            specs = self._visit_step(number, step_config, [])
            steps.extend(specs)

        return steps

    def _visit_step(
        self,
        number,
        step_config,
        visited_steps=None,
        parent_options=None,
        from_flow=None,
    ):
        """
        for each step (as defined in the flow YAML), _visit_step is called with only
        the first two parameters. this takes care of validating the step, collating the
        option overrides, and if it is a task, creating a StepSpec for it.

        If it is a flow, we recursively call _visit_step with the rest of the parameters of context.

        :param number: LooseVersion representation of the current step number
        :param step_config: the current step's config (dict from YAML)
        :param visited_steps: used when called recursively for nested steps, becomes the return value
        :param parent_options: used when called recursively for nested steps, options from parent flow
        :param from_flow: used when called recursively for nested steps, name of parent flow
        :return: List[StepSpec] a list of all resolved steps including/under the one passed in
        """
        number = LooseVersion(str(number))

        if visited_steps is None:
            visited_steps = []

        if parent_options is None:
            parent_options = {}

        # Step Validation
        # - A step is either a task OR a flow.
        if all(k in step_config for k in ("flow", "task")):
            raise FlowConfigError(
                "Step {} is configured as both a flow AND a task. \n\t{}.".format(
                    number, step_config
                )
            )

        # Skips
        # - either in YAML (with the None string)
        # - or by providing a skip list to the FlowRunner at initialization.
        if (
            ("flow" in step_config and step_config["flow"] == "None")
            or ("task" in step_config and step_config["task"] == "None")
            or ("task" in step_config and step_config["task"] in self.skip)
        ):
            visited_steps.append(
                StepSpec(
                    number,
                    step_config.get("task", step_config.get("flow")),
                    step_config.get("options", {}),
                    from_flow=from_flow,
                    skip=True,  # someday we could use different vals for why skipped
                )
            )
            return visited_steps

        if "task" in step_config:
            name = step_config["task"]

            step_options = copy.deepcopy(parent_options.get(name, {}))
            step_options.update(step_config.get("options", {}))

            if name in self.runtime_options:
                # TODO: Support Runtime Options
                pass

            visited_steps.append(
                StepSpec(
                    number,
                    name,
                    step_options,
                    step_config.get("ignore_failure", False),
                    from_flow=from_flow,
                )
            )
            return visited_steps

        if "flow" in step_config:
            name = step_config["flow"]
            step_options = step_config.get("options", {})
            flow_config = self.project_config.get_flow(name)
            for sub_number, sub_stepconf in flow_config.steps.items():
                # append the flow number to the child number, since its a LooseVersion.
                # e.g. if we're in step 2.3 which references a flow with steps 1-5, it
                #   simply ends up as five steps: 2.3.1, 2.3.2, 2.3.3, 2.3.4, 2.3.5
                num = "{}.{}".format(number, sub_number)
                self._visit_step(
                    num,
                    sub_stepconf,
                    visited_steps,
                    parent_options=step_options,
                    from_flow=name,
                )

        return visited_steps

    def _check_old_yaml_format(self):
        # copied from BaseFlow
        if self.flow_config.steps is None:
            if self.flow_config.tasks:
                raise FlowConfigError(
                    'Old flow syntax detected.  Please change from "tasks" to "steps" in the flow definition.'
                )
            else:
                raise FlowConfigError("No steps found in the flow definition")

    def _check_infinite_flows(self, steps, flows=None):
        """
        Recursively loop through the flow_config and check if there are any cycles.

        :param steps: Set of step definitions to loop through
        :param flows: Flows already visited.
        :return: None
        """
        # copied from BaseFlow
        if flows is None:
            flows = []
        for step in steps.values():
            if "flow" in step:
                flow = step["flow"]
                if flow == "None":
                    continue
                if flow in flows:
                    raise FlowInfiniteLoopError(
                        "Infinite flows detected with flow {}".format(flow)
                    )
                flows.append(flow)
                flow_config = self.project_config.get_flow(flow)
                self._check_infinite_flows(flow_config.steps, flows)

    def _init_org(self):
        """ Test and refresh credentials to the org specified. """
        self.logger.info(
            "Verifying and refreshing credentials for target org {}.".format(
                self.org_config.name
            )
        )
        orig_config = self.org_config.config.copy()
        # attempt to refresh the token
        self.org_config.refresh_oauth_token(self.project_config.keychain)
        if self.org_config.config != orig_config:
            self.logger.info("Org info has changed, updating org in keychain")
            self.project_config.keychain.set_org(self.org_config)

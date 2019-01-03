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
 - Meant to replace the public API of BaseFlow, including override hooks.
 - Precomputes a flat list of steps, instead of running Flow recursively.
 -
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
- * Creates a TaskRunner to run the task and get the result
- * Re-raise any fatal exceptions from the task, if not ignore_failure.
- * collects StepResults into the flow.

TaskRunner:
- Imports the actual task module.
- Constructs an instance of the BaseTask subclass.
- Runs/calls the task instance.
- Returns results or exception into an immutable StepResult

Option values/overrides can be passed in at a number of levels, in increasing order of priority:
- Task default (i.e. `.tasks__TASKNAME__options`)
- Flow definition task options (i.e. `.flows__FLOWNAME__steps__STEPNUM__options`)
- Flow definition subflow options (i.e. `.flows__FLOWNAME__steps__STEPNUM__options__TASKNAME`)
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
from collections import namedtuple
from distutils.version import LooseVersion
from operator import attrgetter

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import FlowConfigError, FlowInfiniteLoopError
from cumulusci.core.utils import import_class


class StepSpec(object):
    """ simple namespace to describe what the flowrunner should do each step """

    __slots__ = (
        "step_num",
        "task_name",
        "task_config",
        "task_class",
        "allow_failure",
        "from_flow",
        "skip",
    )

    def __init__(
        self,
        step_num,
        task_name,
        task_config,
        task_class,
        allow_failure=False,
        from_flow=None,
        skip=None,
    ):
        self.step_num = step_num
        self.task_name = task_name
        self.task_config = task_config
        self.task_class = task_class
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

    @property
    def for_display(self):
        skip = ""
        if self.skip:
            skip = " [SKIP]"
        return "{step_num:8}: {task_name}{skip}".format(
            step_num=self.step_num, task_name=self.task_name, skip=skip
        )


StepResult = namedtuple(
    "StepResult", ["step_num", "task_name", "result", "return_values", "exception"]
)


class FlowState(object):
    """ FlowState - carries context to something else, like a CI job, that needs flow hooks run on it. """

    # state is probably not a great name, but who has time to read design patterns...jk...will rename later tho.
    def __init__(self, ctx=None):
        self.context = ctx

    def pre_flow(self):
        pass

    def post_flow(self):
        pass

    def pre_task(self, step):
        pass

    def post_task(self, step, result):
        pass


class TaskRunner(object):
    def __init__(self, project_config, step, org_config, runtime=None):
        self.project_config = project_config
        self.runtime = runtime
        self.step = step
        self.org_config = org_config

    def _options(self,):
        pass

    def run_step(self, step):
        """
        Run a step.

        :param step: StepSpec
        :return: StepResult
        """

        # TODO: Resolve ^^task_name.return_value style option syntax
        exc = None
        try:
            task = step.task_class(
                self.project_config,
                TaskConfig(step.task_config),  # BaseTask wants a full on TaskConfig
                org_config=self.org_config,
                name=step.task_name,
                stepnum=step.step_num,
                flow=self,  # not actually passing the flow, but that doesn't matter, this is more a run_in_flow.
                # TODO: fix that!
            )
            task()
        except Exception as exc:
            # David, I don't know if this makes any sense.
            task.logger.exception("Exception in task {}".format(step.task_name))
        finally:
            return StepResult(
                step.step_num, step.task_name, task.result, task.return_values, exc
            )


class FlowCoordinator(object):
    def __init__(
        self, runtime, flow_config, name=None, options=None, skip=None, state=None
    ):
        self.project_config = runtime.project_config
        self.runtime = runtime
        self.flow_config = flow_config
        self.name = name
        self.org_config = None

        if not state:
            state = FlowState()
        self.state = state

        # TODO: Support CLI/Runtime Options
        if not options:
            options = {}
        self.runtime_options = options

        if not skip:
            skip = []
        self.skip = skip

        self.results = []

        self.logger = self._init_logger()
        self.steps = self._init_steps()  # type: List[StepSpec]

    def _rule(self, fill="=", length=60, new_line=False):
        self.logger.info("{:{fill}<{length}}".format("", fill=fill, length=length))
        if new_line:
            self.logger.info("")

    def run(self, org_config):
        self.org_config = org_config
        line = "Initializing flow: {}".format(self.__class__.__name__)
        if self.name:
            line = "{} ({})".format(line, self.name)
        self._rule()
        self.logger.info(line)
        self._rule(new_line=True)
        self._init_org()

        self._pre_flow()

        self._rule(fill="-")
        for step in self.steps:
            self.logger.info(step.for_display)
        self._rule(fill="-", new_line=True)

        self.logger.info("Starting execution")
        self._rule(new_line=True)

        try:
            for step in self.steps:
                if step.skip:
                    self._rule(fill="*")
                    self.logger.info("Skipping task: {}".format(step.task_name))
                    self._rule(fill="*", new_line=True)
                    continue

                self._rule(fill="-")
                self.logger.into("Running task: {}".format(step.task_name))
                self._rule(fill="-", new_line=True)

                self._pre_task(step)
                runner = TaskRunner(self.project_config, org_config=org_config)
                result = runner.run_step(step)
                self._post_task(step, result)

                self.results.append(
                    result
                )  # add even a failed result to the result set for the post flow

                if result.exception and not step.allow_failure:
                    raise result.exception  # PY3: raise an exception type we control *from* this exception instead?
        finally:
            self._post_flow()

    def _init_logger(self):
        """
        Returns a logging.Logger-like object to use for the duration of the flow. Tasks will receive this logger
        and getChild(class_name) to get a child logger.

        :return: logging.Logger
        """
        return logging.getLogger("cumulusci.flows").getChild(self.__class__.__name__)

    def _init_steps(self,):
        """
        Given the flow config and everything else, create a list of steps to run, sorted by step number.

        :return: List[StepSpec]
        """
        config_steps = self.flow_config.steps

        self._check_old_yaml_format()
        self._check_infinite_flows(config_steps)

        steps = []

        for number, step_config in config_steps.items():
            specs = self._visit_step(number, step_config, [])
            steps.extend(specs)

        return sorted(steps, key=attrgetter("step_num"))

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
                    None,
                    from_flow=from_flow,
                    skip=True,  # someday we could use different vals for why skipped
                )
            )
            return visited_steps

        if "task" in step_config:
            name = step_config["task"]

            # get the base task_config from the project config, as a dict for easier manipulation.
            # will raise if the task doesn't exist / is invalid
            task_config = copy.deepcopy(self.project_config.get_task(name).config)
            if "options" not in task_config:
                task_config["options"] = {}

            # merge the options together, from task_config all the way down through parent_options
            step_overrides = copy.deepcopy(parent_options.get(name, {}))
            step_overrides.update(step_config.get("options", {}))
            task_config["options"].update(step_overrides)

            # get implementation class. raise/fail if it doesn't exist, because why continue
            try:
                task_class = import_class(task_config["class_path"])
            except (ImportError, AttributeError):
                # TODO: clean this up and raise a taskimporterror or something else correcter.
                raise FlowConfigError("Task named {} has bad classpath")

            if name in self.runtime_options:
                pass

            visited_steps.append(
                StepSpec(
                    number,
                    name,
                    task_config,
                    task_class,
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
                # TODO: how does this work with nested flowveride? what does defining step 2.3.2 later do?
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
            "Verifying and refreshing credentials for the specified org: {}.".format(
                self.org_config.name
            )
        )
        orig_config = self.org_config.config.copy()

        # attempt to refresh the token, this can throw...
        self.org_config.refresh_oauth_token(self.project_config.keychain)

        if self.org_config.config != orig_config:
            self.logger.info("Org info has changed, updating org in keychain")
            self.project_config.keychain.set_org(self.org_config)

    def _pre_flow(self):
        self.state.pre_flow()

    def _post_flow(self):
        self.state.post_flow()

    def _pre_task(self, spec):
        self.state.pre_task(spec)

    def _post_task(self, spec, result):
        self.state.post_tsak(spec, result)

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

- FlowCoordinator: takes a flow_config & runtime options to create a set of StepSpecs
  - Meant to replace the public API of BaseFlow, including override hooks.
  - Precomputes a flat list of steps, instead of running Flow recursively.
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
except ImportError:  # pragma: no cover
    pass

import copy
import logging
from collections import defaultdict
from collections import namedtuple
from distutils.version import LooseVersion
from operator import attrgetter

from jinja2.sandbox import ImmutableSandboxedEnvironment

from cumulusci.core.config import TaskConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.exceptions import FlowConfigError, FlowInfiniteLoopError
from cumulusci.core.utils import import_global

# TODO: define exception types: flowfailure, taskimporterror, etc?

RETURN_VALUE_OPTION_PREFIX = "^^"

jinja2_env = ImmutableSandboxedEnvironment()


class StepSpec(object):
    """ simple namespace to describe what the flowrunner should do each step """

    __slots__ = (
        "step_num",  # type: str
        "task_name",  # type: str
        "task_config",  # type: dict
        "task_class",  # type: str
        "project_config",
        "allow_failure",  # type: bool
        "path",  # type: str
        "skip",  # type: bool
        "when",  # type: str
    )

    def __init__(
        self,
        step_num,
        task_name,
        task_config,
        task_class,
        project_config,
        allow_failure=False,
        from_flow=None,
        skip=None,
        when=None,
    ):
        self.step_num = step_num
        self.task_name = task_name
        self.task_config = task_config
        self.task_class = task_class
        self.project_config = project_config
        self.allow_failure = allow_failure
        self.skip = skip
        self.when = when

        # Store the dotted path to this step.
        # This is not guaranteed to be unique, because multiple steps
        # in the same flow can reference the same task name with different options.
        # It's here to support the ^^flow_name.task_name.attr_name syntax
        # for referencing previous task return values in options.
        if from_flow:
            self.path = ".".join([from_flow, task_name])
        else:
            self.path = task_name

    def __repr__(self):
        skipstr = ""
        if self.skip:
            skipstr = "!SKIP! "
        return (
            f"<{skipstr}StepSpec {self.step_num}:{self.task_name} {self.task_config}>"
        )


StepResult = namedtuple(
    "StepResult",
    ["step_num", "task_name", "path", "result", "return_values", "exception"],
)


class FlowCallback(object):
    """A place for code running a flow to inject callbacks to run during the flow.

    A subclass of FlowCallback can use its own constructor to track context, e.g. to refer to a Django model:

        class CustomFlowCallback(FlowCallback):
            def __init__(self, model):
                self.model = model

            def post_task(self, step, result):
                # do something to record state on self.model

    (An instance of the custom FlowCallback class would be passed to FlowCoordinator.)
    """

    def pre_flow(self, coordinator):
        pass

    def post_flow(self, coordinator):
        pass

    def pre_task(self, step):
        pass

    def post_task(self, step, result):
        pass


class TaskRunner(object):
    """ TaskRunner encapsulates the job of instantiating and running a task.
    """

    def __init__(self, step, org_config, flow=None):
        self.step = step
        self.org_config = org_config
        self.flow = flow

    @classmethod
    def from_flow(cls, flow, step):
        return cls(step, flow.org_config, flow=flow)

    def run_step(self, **options):
        """
        Run a step.

        :return: StepResult
        """

        # Resolve ^^task_name.return_value style option syntax
        task_config = self.step.task_config.copy()
        task_config["options"] = task_config.get("options", {}).copy()
        self.flow.resolve_return_value_options(task_config["options"])

        task_config["options"].update(options)

        task = self.step.task_class(
            self.step.project_config,
            TaskConfig(task_config),
            org_config=self.org_config,
            name=self.step.task_name,
            stepnum=self.step.step_num,
            flow=self.flow,
        )
        self._log_options(task)
        exc = None
        try:
            task()
        except Exception as e:
            self.flow.logger.error(f"Exception in task {self.step.path}")
            exc = e
        return StepResult(
            self.step.step_num,
            self.step.task_name,
            self.step.path,
            task.result,
            task.return_values,
            exc,
        )

    def _log_options(self, task):
        task.logger.info("Options:")
        if not task.task_options:
            return
        for key, info in task.task_options.items():
            value = task.options.get(key)
            if value is not None:
                task.logger.info(f"  {key}: {value}")


class FlowCoordinator(object):
    def __init__(
        self,
        project_config,
        flow_config,
        name=None,
        options=None,
        skip=None,
        callbacks=None,
    ):
        self.project_config = project_config
        self.flow_config = flow_config
        self.name = name
        self.org_config = None

        if not callbacks:
            callbacks = FlowCallback()
        self.callbacks = callbacks

        self.runtime_options = options or {}

        if not skip:
            skip = []
        self.skip = skip

        self.results = []

        self.logger = self._init_logger()
        self.steps = self._init_steps()  # type: List[StepSpec]

    @classmethod
    def from_steps(cls, project_config, steps, name=None, callbacks=None):
        instance = cls(
            project_config,
            flow_config=FlowConfig({"steps": {}}),
            name=name,
            callbacks=callbacks,
        )
        instance.steps = steps
        return instance

    def _rule(self, fill="=", length=60, new_line=False):
        self.logger.info(f"{fill * length}")
        if new_line:
            self.logger.info("")

    def get_summary(self):
        """ Returns an output string that contains the description of the flow,
            the sequence of tasks and subflows, and any "when" conditions associated
            with tasks. """
        lines = []
        if "description" in self.flow_config.config:
            lines.append(f"Description: {self.flow_config.config['description']}")
        previous_parts = []
        previous_source = None
        for step in self.steps:
            parts = step.path.split(".")
            steps = str(step.step_num).split("/")
            if len(parts) > len(steps):
                # Sub-step generated during freeze process; skip it
                continue
            task_name = parts.pop()

            i = -1
            new_source = (
                f" [from {step.project_config.source}]"
                if step.project_config.source is not previous_source
                else ""
            )
            for i, flow_name in enumerate(parts):
                if not any(":" in part for part in step.path.split(".")[i + 1 :]):
                    source = new_source
                else:
                    source = ""
                if len(previous_parts) < i + 1 or previous_parts[i] != flow_name:
                    lines.append(f"{'    ' * i}{steps[i]}) flow: {flow_name}{source}")
                    if source:
                        new_source = ""

            padding = "    " * (i + 1) + " " * len(str(steps[i + 1]))
            when = f"\n{padding}  when: {step.when}" if step.when is not None else ""
            lines.append(
                f"{'    ' * (i + 1)}{steps[i + 1]}) task: {task_name}{new_source}{when}"
            )
            previous_parts = parts
            previous_source = step.project_config.source
        return "\n".join(lines)

    def run(self, org_config):
        self.org_config = org_config
        line = f"Initializing flow: {self.__class__.__name__}"
        if self.name:
            line = f"{line} ({self.name})"
        self._rule()
        self.logger.info(line)
        self.logger.info(self.flow_config.description)
        self._rule(new_line=True)

        self._init_org()
        self._rule(fill="-")
        self.logger.info("Organization:")
        self.logger.info(f"  Username: {org_config.username}")
        self.logger.info(f"    Org Id: {org_config.org_id}")
        self._rule(fill="-", new_line=True)

        # Give pre_flow callback a chance to alter the steps
        # based on the state of the org before we display the steps.
        self.callbacks.pre_flow(self)

        self._rule(fill="-")
        self.logger.info("Steps:")
        for line in self.get_summary().splitlines():
            self.logger.info(line)
        self._rule(fill="-", new_line=True)

        self.logger.info("Starting execution")
        self._rule(new_line=True)

        try:
            for step in self.steps:
                if step.skip:
                    self._rule(fill="*")
                    self.logger.info(f"Skipping task: {step.task_name}")
                    self._rule(fill="*", new_line=True)
                    continue

                if step.when:
                    jinja2_context = {
                        "project_config": step.project_config,
                        "org_config": self.org_config,
                    }
                    expr = jinja2_env.compile_expression(step.when)
                    value = expr(**jinja2_context)
                    if not value:
                        self.logger.info(
                            f"Skipping task {step.task_name} (skipped unless {step.when})"
                        )
                        continue

                self._rule(fill="-")
                self.logger.info(f"Running task: {step.task_name}")
                self._rule(fill="-", new_line=True)

                self.callbacks.pre_task(step)
                result = TaskRunner.from_flow(self, step).run_step()
                self.callbacks.post_task(step, result)

                self.results.append(
                    result
                )  # add even a failed result to the result set for the post flow

                if result.exception and not step.allow_failure:
                    raise result.exception  # PY3: raise an exception type we control *from* this exception instead?
        finally:
            self.callbacks.post_flow(self)

    def _init_logger(self):
        """
        Returns a logging.Logger-like object to use for the duration of the flow. Tasks will receive this logger
        and getChild(class_name) to get a child logger.

        :return: logging.Logger
        """
        return logging.getLogger("cumulusci.flows").getChild(self.__class__.__name__)

    def _init_steps(self):
        """
        Given the flow config and everything else, create a list of steps to run, sorted by step number.

        :return: List[StepSpec]
        """
        self._check_old_yaml_format()
        self._check_infinite_flows(self.flow_config)

        steps = []

        for number, step_config in self.flow_config.steps.items():
            specs = self._visit_step(number, step_config, self.project_config)
            steps.extend(specs)

        return sorted(steps, key=attrgetter("step_num"))

    def _visit_step(
        self,
        number,
        step_config,
        project_config,
        visited_steps=None,
        parent_options=None,
        parent_ui_options=None,
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
        :param parent_ui_options: used when called recursively for nested steps, UI options from parent flow
        :param from_flow: used when called recursively for nested steps, name of parent flow
        :return: List[StepSpec] a list of all resolved steps including/under the one passed in
        """
        number = LooseVersion(str(number))

        if visited_steps is None:
            visited_steps = []
        if parent_options is None:
            parent_options = {}
        if parent_ui_options is None:
            parent_ui_options = {}

        # Step Validation
        # - A step is either a task OR a flow.
        if all(k in step_config for k in ("flow", "task")):
            raise FlowConfigError(
                f"Step {number} is configured as both a flow AND a task. \n\t{step_config}."
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
                    step_num=number,
                    task_name=step_config.get("task", step_config.get("flow")),
                    task_config=step_config.get("options", {}),
                    task_class=None,
                    project_config=project_config,
                    from_flow=from_flow,
                    skip=True,  # someday we could use different vals for why skipped
                )
            )
            return visited_steps

        if "task" in step_config:
            name = step_config["task"]

            # get the base task_config from the project config, as a dict for easier manipulation.
            # will raise if the task doesn't exist / is invalid
            task_config = project_config.get_task(name)
            task_config_dict = copy.deepcopy(task_config.config)
            if "options" not in task_config_dict:
                task_config_dict["options"] = {}

            # merge the options together, from task_config all the way down through parent_options
            step_overrides = copy.deepcopy(parent_options.get(name, {}))
            step_overrides.update(step_config.get("options", {}))
            task_config_dict["options"].update(step_overrides)

            # merge UI options from task config and parent flow
            if "ui_options" not in task_config_dict:
                task_config_dict["ui_options"] = {}
            step_ui_overrides = copy.deepcopy(parent_ui_options.get(name, {}))
            step_ui_overrides.update(step_config.get("ui_options", {}))
            task_config_dict["ui_options"].update(step_ui_overrides)

            # merge checks from task config and flow step
            if "checks" not in task_config_dict:
                task_config_dict["checks"] = []
            task_config_dict["checks"].extend(step_config.get("checks", []))

            # merge runtime options
            if name in self.runtime_options:
                task_config_dict["options"].update(self.runtime_options[name])

            # get implementation class. raise/fail if it doesn't exist, because why continue
            try:
                task_class = import_global(task_config_dict["class_path"])
            except (ImportError, AttributeError):
                raise FlowConfigError(f"Task named {name} has bad classpath")

            visited_steps.append(
                StepSpec(
                    step_num=number,
                    task_name=name,
                    task_config=task_config_dict,
                    task_class=task_class,
                    project_config=task_config.project_config,
                    allow_failure=step_config.get("ignore_failure", False),
                    from_flow=from_flow,
                    when=step_config.get("when"),
                )
            )
            return visited_steps

        if "flow" in step_config:
            name = step_config["flow"]
            if from_flow:
                path = ".".join([from_flow, name])
            else:
                path = name
            step_options = step_config.get("options", {})
            step_ui_options = step_config.get("ui_options", {})
            flow_config = project_config.get_flow(name)
            for sub_number, sub_stepconf in flow_config.steps.items():
                # append the flow number to the child number, since its a LooseVersion.
                # e.g. if we're in step 2.3 which references a flow with steps 1-5, it
                #   simply ends up as five steps: 2.3.1, 2.3.2, 2.3.3, 2.3.4, 2.3.5
                # TODO: how does this work with nested flowveride? what does defining step 2.3.2 later do?
                num = f"{number}/{sub_number}"
                self._visit_step(
                    number=num,
                    step_config=sub_stepconf,
                    project_config=flow_config.project_config,
                    visited_steps=visited_steps,
                    parent_options=step_options,
                    parent_ui_options=step_ui_options,
                    from_flow=path,
                )
        return visited_steps

    def _check_old_yaml_format(self):
        if self.flow_config.steps is None:
            if "tasks" in self.flow_config.config:
                raise FlowConfigError(
                    'Old flow syntax detected.  Please change from "tasks" to "steps" in the flow definition.'
                )
            else:
                raise FlowConfigError("No steps found in the flow definition")

    def _check_infinite_flows(self, flow_config, visited_flows=None):
        """
        Recursively loop through the flow_config and check if there are any cycles.

        :param steps: Set of step definitions to loop through
        :param flows: Flows already visited.
        :return: None
        """
        if visited_flows is None:
            visited_flows = set()
        project_config = flow_config.project_config
        for step in flow_config.steps.values():
            if "flow" in step:
                flow_name = step["flow"]
                if flow_name == "None":
                    continue
                next_flow_config = project_config.get_flow(flow_name)
                signature = (
                    hash(next_flow_config.project_config.source),
                    next_flow_config.name,
                )
                if signature in visited_flows:
                    raise FlowInfiniteLoopError(
                        f"Infinite flows detected with flow {flow_name}"
                    )
                visited_flows.add(signature)
                self._check_infinite_flows(next_flow_config, visited_flows)

    def _init_org(self):
        """ Test and refresh credentials to the org specified. """
        self.logger.info(
            f"Verifying and refreshing credentials for the specified org: {self.org_config.name}."
        )
        orig_config = self.org_config.config.copy()

        # attempt to refresh the token, this can throw...
        self.org_config.refresh_oauth_token(self.project_config.keychain)

        if self.org_config.config != orig_config:
            self.logger.info("Org info has changed, updating org in keychain")
            self.project_config.keychain.set_org(self.org_config)

    def resolve_return_value_options(self, options):
        """Handle dynamic option value lookups in the format ^^task_name.attr"""
        for key, value in options.items():
            if isinstance(value, str) and value.startswith(RETURN_VALUE_OPTION_PREFIX):
                path, name = value[len(RETURN_VALUE_OPTION_PREFIX) :].rsplit(".", 1)
                result = self._find_result_by_path(path)
                options[key] = result.return_values.get(name)

    def _find_result_by_path(self, path):
        for result in self.results:
            if result.path[-len(path) :] == path:
                return result
        raise NameError(f"Path not found: {path}")


class PreflightFlowCoordinator(FlowCoordinator):
    """Coordinates running preflight checks instead of the actual flow steps.
    """

    def run(self, org_config):
        self.org_config = org_config
        self.callbacks.pre_flow(self)

        self._init_org()
        self._rule(fill="-")
        self.logger.info("Organization:")
        self.logger.info(f"  Username: {org_config.username}")
        self.logger.info(f"    Org Id: {org_config.org_id}")
        self._rule(fill="-", new_line=True)

        self.logger.info("Running preflight checks...")
        self._rule(new_line=True)

        self.preflight_results = defaultdict(list)
        self._task_cache = TaskCache(self)
        try:
            # flow-level checks
            jinja2_context = {
                "tasks": self._task_cache,
                "project_config": self.project_config,
                "org_config": self.org_config,
            }
            for check in self.flow_config.checks or []:
                result = self.evaluate_check(check, jinja2_context)
                if result:
                    self.preflight_results[None].append(result)

            # Step-level checks
            for step in self.steps:
                jinja2_context["project_config"] = step.project_config
                for check in step.task_config.get("checks", []):
                    result = self.evaluate_check(check, jinja2_context)
                    if result:
                        self.preflight_results[str(step.step_num)].append(result)
        finally:
            self.callbacks.post_flow(self)

    def evaluate_check(self, check, jinja2_context):
        self.logger.info(f"Evaluating check: {check['when']}")
        expr = jinja2_env.compile_expression(check["when"])
        value = bool(expr(**jinja2_context))
        self.logger.info(f"Check result: {value}")
        if value:
            return {"status": check["action"], "message": check.get("message")}


class TaskCache(object):
    """Provides access to named tasks and caches their results.

    This is intended for use in a jinja2 expression context
    so that multiple expressions evaluated in the same context
    can avoid running a task more than once with the same options.
    """

    def __init__(self, flow):
        self.flow = flow
        self.results = {}

    def __getattr__(self, task_name):
        return CachedTaskRunner(self, task_name)


class CachedTaskRunner(object):
    """Runs a task and caches the result in a TaskCache"""

    def __init__(self, cache, task_name):
        self.cache = cache
        self.task_name = task_name

    def __call__(self, **options):
        cache_key = (self.task_name, tuple(sorted(options.items())))
        if cache_key in self.cache.results:
            return self.cache.results[cache_key].return_values

        task_config = self.cache.flow.project_config.tasks[self.task_name]
        task_class = import_global(task_config["class_path"])
        step = StepSpec(
            step_num=1,
            task_name=self.task_name,
            task_config=task_config,
            task_class=task_class,
            project_config=self.cache.flow.project_config,
        )
        self.cache.flow.callbacks.pre_task(step)
        result = TaskRunner(step, self.cache.flow.org_config, self.cache.flow).run_step(
            **options
        )
        self.cache.flow.callbacks.post_task(step, result)

        self.cache.results[cache_key] = result
        return result.return_values

"""Utilities for working with MetaDeploy plans"""

from cumulusci.core.config import FlowConfig, TaskConfig
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.utils import cd


def get_frozen_steps(project_config, plan_config):
    """Return a list of frozen steps for a MetaDeploy plan config"""
    flow_config = FlowConfig(plan_config)
    flow_config.project_config = project_config
    flow = FlowCoordinator(project_config, flow_config)
    steps = []
    for step in flow.steps:
        if step.skip:
            continue
        with cd(step.project_config.repo_root):
            task = step.task_class(
                step.project_config,
                TaskConfig(step.task_config),
                name=step.task_name,
            )
            steps.extend(task.freeze(step))
    return steps

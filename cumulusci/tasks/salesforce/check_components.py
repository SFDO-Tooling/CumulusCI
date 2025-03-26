import json
import os
import shutil
import tempfile
from collections import defaultdict
from itertools import chain
from xml.etree.ElementTree import ParseError

from defusedxml.minidom import parseString

from cumulusci.core.config import FlowConfig, TaskConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.core.sfdx import convert_sfdx_source
from cumulusci.core.utils import process_list_arg
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.metadata.package import process_common_components
from cumulusci.tasks.salesforce import BaseSalesforceTask
from cumulusci.utils import cd
from cumulusci.utils.xml import metadata_tree


class CheckComponents(BaseSalesforceTask):
    api_retrieve_unpackaged = ApiRetrieveUnpackaged
    task_options = {
        "paths": {
            "description": "List of deploy paths to check",
            "required": False,
        },
        "name": {
            "description": "The name of the current plan or flow to detect deploy paths",
            "required": False,
        },
    }
    deploy_paths = []

    def _init_options(self, kwargs):
        super(CheckComponents, self)._init_options(kwargs)
        if "paths" in self.options and "name" in self.options:
            raise TaskOptionsError("Please provide either --paths or --name")
        if "paths" not in self.options and "name" not in self.options:
            raise TaskOptionsError(
                "This task requires a plan/flow name or paths options. Pass --paths or --name options"
            )

    def _run_task(self):
        # Check if paths are provided in options. Assuming to only check for those paths
        paths = self.options.get("paths")
        plan_or_flow_name = self.options.get("name")

        (
            components,
            api_retrieve_unpackaged_response,
        ) = self.get_repo_existing_components(plan_or_flow_name, paths)

        if not components:
            self.logger.info("No components found in deploy path")
            raise TaskOptionsError("No plan or paths options provided")

        self.logger.debug("Components detected at source")
        for component_type, component_names in components.items():
            self.logger.debug(f"{component_type}: {', '.join(component_names)}")
        # check common components
        components.pop("Settings", None)
        existing_components = process_common_components(
            api_retrieve_unpackaged_response, components
        )

        if existing_components:
            self.logger.info("Components exists in the target org:")
            for component_type, component_names in existing_components.items():
                self.logger.info(f"{component_type}: {', '.join(component_names)}")
            self.return_values["existing_components"] = existing_components
        else:
            self.logger.info(
                "No components from the deploy paths exist in the target org."
            )

    def get_repo_existing_components(self, plan_or_flow_name, paths=""):
        if paths:
            paths = process_list_arg(paths)
            self.logger.info(f"Using provided paths: {paths}")
            self.deploy_paths = paths
        elif plan_or_flow_name:
            # if path is not provided
            is_plan = self._is_plan(plan_or_flow_name)
            if is_plan is None:
                raise TaskOptionsError(
                    f"Plan or flow name '{plan_or_flow_name}' not found"
                )

            self.logger.info(
                f"Analyzing project {'plan' if is_plan else 'flow'}: {plan_or_flow_name}"
            )

            # load deploy paths from all the steps in plan or flow
            self._load_deploy_paths(plan_or_flow_name, is_plan)
            if not self.deploy_paths:
                self.logger.warning("No deploy paths found in the plan or flow.")
                return
            self.logger.debug(
                f"deploy paths found in the plan or flow.{self.deploy_paths}"
            )
        # Temp dir to copy all deploy paths from task options
        temp_dir = tempfile.mkdtemp()
        self.logger.info(f"Temporary deploy directory created: {temp_dir}")
        mdapi_components = {}
        mdapi_response_messages = []
        for path in self.deploy_paths:
            full_path = os.path.join(self.project_config.repo_root, path)
            if not os.path.exists(full_path):
                self.logger.info(f"Skipping path: '{path}' - path doesn't exist")
                continue
            elif "package.xml" in os.listdir(full_path):
                package_xml_path = os.path.join(full_path, "package.xml")
                source_xml_tree = metadata_tree.parse(package_xml_path)
                components = metadata_tree.parse_package_xml_types(
                    "name", source_xml_tree
                )
                response_messages = self._get_api_object_responce(
                    package_xml_path, source_xml_tree.version.text
                )
                merged = {}
                for key in set(components).union(mdapi_components):
                    merged[key] = list(
                        set(
                            chain(
                                components.get(key, []), mdapi_components.get(key, [])
                            )
                        )
                    )
                mdapi_components = merged
                mdapi_response_messages.extend(response_messages)
                continue
            self._copy_to_tempdir(path, temp_dir)

        (
            components,
            api_retrieve_unpackaged_response,
        ) = self._collect_components_from_paths(temp_dir)

        # remove temp dir
        shutil.rmtree(temp_dir)
        merged = {}
        if components:
            for key in set(components).union(mdapi_components):
                merged[key] = list(
                    set(chain(components.get(key, []), mdapi_components.get(key, [])))
                )
            components = merged
        else:
            components = mdapi_components

        if api_retrieve_unpackaged_response:
            api_retrieve_unpackaged_response.extend(mdapi_response_messages)
        else:
            api_retrieve_unpackaged_response = mdapi_response_messages

        return [components, api_retrieve_unpackaged_response]

    def _copy_to_tempdir(self, src_dir, temp_dir):
        for item in os.listdir(src_dir):
            src_item = os.path.join(src_dir, item)
            dst_item = os.path.join(temp_dir, item)

            if os.path.isdir(src_item):
                if not os.path.exists(dst_item):
                    shutil.copytree(src_item, dst_item)
                else:
                    self._merge_directories(src_item, dst_item)
            else:
                if not os.path.exists(dst_item):
                    shutil.copy2(src_item, dst_item)
                else:
                    self.logger.debug(f"File {dst_item} already exists, skipping...")

    def _merge_directories(self, src_dir, dst_dir):
        for item in os.listdir(src_dir):
            src_item = os.path.join(src_dir, item)
            dst_item = os.path.join(dst_dir, item)

            if os.path.isdir(src_item):
                if not os.path.exists(dst_item):
                    shutil.copytree(src_item, dst_item)
                    self._merge_directories(src_item, dst_item)
            else:
                if not os.path.exists(dst_item):
                    shutil.copy2(src_item, dst_item)  # Copy file if it doesn't exist
                else:
                    self.logger.debug(f"File {dst_item} already exists, skipping...")

    def _is_plan(self, name):

        if self.project_config.lookup(f"plans__{name}") is not None:
            return True
        elif self.project_config.lookup(f"flows__{name}") is not None:
            return False
        else:
            raise TaskOptionsError(
                "No paths provided and unable to determine the current plan or flow name."
            )

    def _get_plan_tasks(self, name, is_plan=False):

        tasks = []
        if is_plan:
            step_config = self.project_config.lookup(f"plans__{name}")
        else:
            step_config = self.project_config.lookup(f"flows__{name}")

        tasks = self._freeze_steps(self.project_config, step_config)

        return tasks

    def _freeze_steps(self, project_config, plan_config) -> list:
        steps = plan_config["steps"]
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
        self.logger.debug("Prepared steps:\n" + json.dumps(steps, indent=4))
        return steps

    def _load_deploy_paths(self, name, is_plan=False):
        tasks = self._get_plan_tasks(name, is_plan)
        if tasks:
            self.deploy_paths = self._get_deployable_paths(tasks)

    def _get_deployable_paths(self, tasks):
        found_paths = []
        paths_to_search = ["path", "subfolder"]
        for task in tasks:
            if "task_config" in task and "options" in task["task_config"]:
                options = task["task_config"]["options"]
                found_paths.extend(self._search_for_paths(options, paths_to_search))
        return found_paths

    def _search_for_paths(self, options, keys_to_search):
        found_values = []

        if not keys_to_search:
            return found_values

        def recursive_search(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in keys_to_search and isinstance(value, str):
                        found_values.append(value)
                    elif isinstance(value, (dict, list)):
                        recursive_search(value)

            elif isinstance(obj, list):
                for item in obj:
                    recursive_search(item)

        recursive_search(options)

        return found_values

    def _collect_components_from_paths(self, full_path):

        if not os.path.exists(full_path):
            return None, None

        components = defaultdict(set)
        self.logger.info(f"Collecting components from path: {full_path}")
        # remove if any exiting package.xml files coppied from deploy_pre/post paths

        if os.path.exists(os.path.join(full_path, "package.xml")):
            os.remove(os.path.join(full_path, "package.xml"))

        with convert_sfdx_source(full_path, None, self.logger) as src_path:
            package_xml_path = os.path.join(src_path, "package.xml")
            if os.path.exists(package_xml_path):
                try:
                    source_xml_tree = metadata_tree.parse(package_xml_path)
                    self.logger.info("parsing package.xml")

                    components = metadata_tree.parse_package_xml_types(
                        "name", source_xml_tree
                    )

                    response_messages = self._get_api_object_responce(
                        package_xml_path, source_xml_tree.version.text
                    )

                    return [components, response_messages]

                except ParseError as e:
                    self.logger.error(f"Error parsing package.xml: {e}")
                    return None, None
            else:
                self.logger.warning(
                    f"No package.xml found in {full_path}, scanning directories"
                )

        return None, None

    def _get_api_object_responce(self, pakcage_xml_path, version):

        if not os.path.exists(pakcage_xml_path):
            return None

        package_xml = open(pakcage_xml_path, "r")

        api_retrieve_unpackaged_object = self.api_retrieve_unpackaged(
            self, package_xml.read(), version
        )

        response_messages = parseString(
            api_retrieve_unpackaged_object._get_response().content
        ).getElementsByTagName("messages")

        return response_messages

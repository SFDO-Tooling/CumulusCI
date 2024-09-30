import os
from collections import defaultdict
from xml.etree.ElementTree import ParseError

from defusedxml.minidom import parseString

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.sfdx import convert_sfdx_source
from cumulusci.salesforce_api.metadata import ApiRetrieveUnpackaged
from cumulusci.tasks.salesforce import BaseSalesforceTask
from cumulusci.utils.xml import metadata_tree


class CheckComponents(BaseSalesforceTask):
    api_retrieve_unpackaged = ApiRetrieveUnpackaged
    task_options = {
        "paths": {
            "description": "List of deploy paths to check",
            "required": False,
        },
        "plan_name": {
            "description": "The name of the current plan",
            "required": False,
        },
        "flow_name": {
            "description": "The name of the current flow",
            "required": False,
        },
    }

    def _run_task(self):
        # Check if paths are provided in options
        paths = self.options.get("paths")
        if paths:
            if isinstance(paths, str):
                paths = [path.strip() for path in paths.split(",")]
            self.logger.info(f"Using provided paths: {paths}")
            deploy_paths = paths
        else:
            plan_or_flow_name, is_plan = self._get_current_plan_or_flow_name()
            if not plan_or_flow_name:
                raise TaskOptionsError(
                    "No paths provided and unable to determine the current plan or flow name."
                )
            self.logger.info(
                f"Analyzing {'plan' if is_plan else 'flow'}: {plan_or_flow_name}"
            )
            steps = self._get_plan_or_flow_steps(plan_or_flow_name, is_plan)
            deploy_paths = self._get_deploy_paths_from_steps(steps)
            if not deploy_paths:
                self.logger.info("No deploy paths found in the plan or flow.")
                return

        self.logger.info(f"deploy paths found in the plan or flow.{deploy_paths}")
        for path in deploy_paths:
            full_path = os.path.join(self.project_config.repo_root, path)
            if not os.path.exists(full_path):
                self.logger.warning(f"Path does not exist: {full_path}")
                continue

            (
                components,
                api_retrieve_unpackaged_response,
            ) = self._collect_components_from_paths(full_path)
            if not components:
                self.logger.info("No components found in deploy paths.")
                return

            existing_components = self._check_components_in_org(
                components, api_retrieve_unpackaged_response
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

    def _get_current_plan_or_flow_name(self):
        plan_name = self.options.get("plan_name")
        flow_name = self.options.get("flow_name")

        if plan_name:
            return plan_name, True
        elif flow_name:
            return flow_name, False
        else:
            plan_name = getattr(self.project_config, "plan_name", None)
            flow_name = getattr(self.project_config, "flow_name", None)
            if plan_name:
                return plan_name, True
            elif flow_name:
                return flow_name, False
            else:
                return None, None

    def _get_plan_or_flow_steps(self, name, is_plan=False):
        collection = self.project_config.plans if is_plan else self.project_config.flows
        if name not in collection:
            raise TaskOptionsError(
                f"{'Plan' if is_plan else 'Flow'} '{name}' not found in project configuration."
            )
        item = collection[name]
        steps = item.get("steps", {})
        return steps

    def _get_deploy_paths_from_steps(self, steps):
        deploy_paths = []
        for step_num, step in steps.items():
            # Handle tasks
            if "task" in step:
                task_name = step.get("task")
                options = step.get("options", {})
                # If the task is 'deploy', collect the path
                if task_name == "deploy":
                    path = options.get("path")
                    if path and path not in deploy_paths:
                        deploy_paths.append(path)
                # If the task is 'flow', recursively get deploy paths
                elif task_name == "flow":
                    flow_name = options.get("flow")
                    if flow_name:
                        self.logger.info(f"Recursing into flow: {flow_name}")
                        flow_steps = self._get_plan_or_flow_steps(flow_name)
                        deploy_paths.extend(
                            self._get_deploy_paths_from_steps(flow_steps)
                        )
            elif "flow" in step:
                flow_name = step["flow"]
                self.logger.info(f"Recursing into flow: {flow_name}")
                flow_steps = self._get_plan_or_flow_steps(flow_name)
                deploy_paths.extend(self._get_deploy_paths_from_steps(flow_steps))
            # Handle nested steps
            elif "steps" in step:
                nested_steps = step["steps"]
                deploy_paths.extend(self._get_deploy_paths_from_steps(nested_steps))
            else:
                options = step.get("options", {})
                path = options.get("path")
                if path and path not in deploy_paths:
                    deploy_paths.append(path)
        return deploy_paths

    def _collect_components_from_paths(self, full_path):
        components = defaultdict(set)
        self.logger.info(f"Collecting components from path: {full_path}")

        with convert_sfdx_source(full_path, None, self.logger) as src_path:
            package_xml_path = os.path.join(src_path, "package.xml")
            if os.path.exists(package_xml_path):
                try:
                    source_xml_tree = metadata_tree.parse(package_xml_path)
                    self.logger.info(f"parsing package.xml: {source_xml_tree}")
                    for types_element in source_xml_tree.findall("types"):
                        members = [
                            member.text for member in types_element.findall("members")
                        ]
                        name = types_element.find("name").text
                        components[name].update(members)

                    response_messages = self._get_api_object_responce(
                        package_xml_path, source_xml_tree.version.text
                    )

                    return [components, response_messages]

                except ParseError as e:
                    self.logger.error(f"Error parsing package.xml: {e}")
                    return None
            else:
                self.logger.info(
                    f"No package.xml found in {full_path}, scanning directories"
                )

        return None

    def _get_api_object_responce(self, pakcage_xml_path, version):
        package_xml = open(pakcage_xml_path, "r")

        api_retrieve_unpackaged_object = self.api_retrieve_unpackaged(
            self, package_xml.read(), version
        )

        response_messages = parseString(
            api_retrieve_unpackaged_object._get_response().content
        ).getElementsByTagName("messages")

        return response_messages

    def _check_components_in_org(self, components, response_messages):

        for message in response_messages:
            message_list = message.firstChild.nextSibling.firstChild.nodeValue.split(
                "'"
            )
            component_type = message_list[1]
            message_txt = message_list[2]

            if "is not available in this organization" in message_txt:
                del components[component_type]
            else:
                component_name = message_list[3]
                if component_name in components[component_type]:
                    components[component_type].remove(component_name)
                    if len(components[component_type]) == 0:
                        del components[component_type]

        return components

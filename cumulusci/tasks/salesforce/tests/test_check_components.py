import os
from unittest.mock import MagicMock, mock_open, patch

from cumulusci.tasks.salesforce.check_components import CheckComponents

from .util import create_task


class TestCheckComponents:

    def test_get_current_plan_or_flow_name_with_options(self):
        task = create_task(CheckComponents, {"plan_name": "test_plan"})

        plan_name, is_plan = task._get_current_plan_or_flow_name()
        assert plan_name == "test_plan"
        assert is_plan is True

        task.options = {"flow_name": "test_flow"}
        plan_name, is_plan = task._get_current_plan_or_flow_name()
        assert plan_name == "test_flow"
        assert is_plan is False

    def test_get_current_plan_or_flow_name_from_project_config(self):
        task = create_task(CheckComponents, {})

        task.project_config.plan_name = "config_plan"

        plan_name, is_plan = task._get_current_plan_or_flow_name()
        assert plan_name == "config_plan"
        assert is_plan is True

        task.project_config.plan_name = None
        task.project_config.flow_name = "config_flow"
        plan_name, is_plan = task._get_current_plan_or_flow_name()
        assert plan_name == "config_flow"
        assert is_plan is False

    def test_get_plan_or_flow_steps_plan(self):
        task = create_task(CheckComponents, {})

        task.project_config.plans = {
            "test_plan": {
                "steps": {"1": {"task": "deploy", "options": {"path": "force-app"}}}
            }
        }

        steps = task._get_plan_or_flow_steps("test_plan", is_plan=True)
        assert "1" in steps
        assert steps["1"]["task"] == "deploy"

    def test_get_plan_or_flow_steps_flow(self):
        task = create_task(CheckComponents, {})

        task.project_config.flows = {
            "test_flow": {
                "steps": {"1": {"task": "deploy", "options": {"path": "force-app"}}}
            }
        }

        steps = task._get_plan_or_flow_steps("test_flow", is_plan=False)
        assert "1" in steps
        assert steps["1"]["task"] == "deploy"

    def test_get_deploy_paths_from_steps(self):
        task = create_task(CheckComponents, {})

        steps = {
            "1": {"task": "deploy", "options": {"path": "path1"}},
            "2": {"task": "deploy", "options": {"path": "path2"}},
            "3": {"flow": "sub_flow"},
        }

        task.project_config.config["flows"] = {
            "sub_flow": {
                "steps": {"1": {"task": "deploy", "options": {"path": "path3"}}}
            }
        }

        deploy_paths = task._get_deploy_paths_from_steps(steps)
        assert deploy_paths == ["path1", "path2", "path3"], f"deploy_paths: {steps}"

    @patch("os.path.exists")
    @patch("os.path.isdir")
    @patch("os.listdir")
    @patch("os.path.join")
    @patch("cumulusci.core.sfdx.convert_sfdx_source")
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data="""
        <Package xmlns="http://soap.sforce.com/2006/04/metadata">
            <types>
                <members>Delivery</members>
                <name>ApexClass</name>
            </types>
            <types>
                <members>Delivery__c</members>
                <name>CustomObject</name>
            </types>
            <version>58.0</version>
        </Package>
    """,
    )
    @patch("cumulusci.utils.xml.metadata_tree.parse")
    def test_collect_components_from_paths(
        self,
        mock_metadata_parse,
        mock_open_file,
        mock_convert_sfdx_source,
        mock_path_join,
        mock_listdir,
        mock_isdir,
        mock_path_exists,
    ):

        mock_path_exists.return_value = True
        mock_path_join.side_effect = lambda *args: os.path.sep.join(args)
        mock_convert_sfdx_source.return_value.__enter__.return_value = (
            "/src_convrt/path"
        )

        mock_tree = MagicMock()
        mock_tree.findall.return_value = [
            MagicMock(
                findall=lambda tag: (
                    [MagicMock(text="Delivery")] if tag == "members" else []
                ),
                find=lambda tag: MagicMock(text="ApexClass") if tag == "name" else None,
            ),
            MagicMock(
                findall=lambda tag: (
                    [MagicMock(text="Delivery__c")] if tag == "members" else []
                ),
                find=lambda tag: (
                    MagicMock(text="CustomObject") if tag == "name" else None
                ),
            ),
        ]

        mock_tree.version.text = "58.0"
        mock_metadata_parse.return_value = mock_tree

        response_messages = [
            MagicMock(
                firstChild=MagicMock(
                    nextSibling=MagicMock(
                        firstChild=MagicMock(
                            nodeValue="Entity of type 'ApexClass' named 'CustomHealth' is cannot be found"
                        )
                    )
                )
            )
        ]

        with patch.object(
            CheckComponents, "_get_api_object_responce"
        ) as mock_get_api_response:
            mock_get_api_response.return_value = response_messages

            task = create_task(CheckComponents, {})

            components, api_response = task._collect_components_from_paths("/fake/path")

            assert "ApexClass" in components
            assert "Delivery" in components["ApexClass"]
            assert "CustomObject" in components
            assert "Delivery__c" in components["CustomObject"]
            assert api_response == response_messages

    def test_check_components_in_org(self):

        components = {
            "ApexClass": {"Delivery"},
            "CustomObject": {"Delivery__c"},
        }

        response_messages = [
            MagicMock(
                firstChild=MagicMock(
                    nextSibling=MagicMock(
                        firstChild=MagicMock(
                            nodeValue="Entity of type 'ApexClass' named 'Delivery' cannot be found"
                        )
                    )
                )
            ),
        ]

        task = create_task(CheckComponents, {})

        existing_components = task._check_components_in_org(
            components, response_messages
        )

        assert "ApexClass" not in existing_components
        assert "CustomObject" in existing_components
        assert existing_components["CustomObject"] == {"Delivery__c"}

    def test_get_api_object_responce(self):
        package_xml_path = "/fake/path/package.xml"
        version = "58.0"

        mock_api_retrieve_unpackaged = MagicMock()
        mock_api_retrieve_unpackaged_object = MagicMock()
        mock_api_retrieve_unpackaged.return_value = mock_api_retrieve_unpackaged_object

        mock_api_retrieve_unpackaged_object._get_response.return_value.content = b"""
            <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">
                <soapenv:Body>
                    <retrieveResponse xmlns="http://soap.sforce.com/2006/04/metadata">
                        <result>
                            <messages>
                                <problem>Entity of type 'ApexClass' named 'Delivery' cannot be found</problem>
                                <fileName>classes/Delivery.cls</fileName>
                            </messages>
                        </result>
                    </retrieveResponse>
                </soapenv:Body>
            </soapenv:Envelope>
        """

        with patch.object(
            CheckComponents, "api_retrieve_unpackaged", mock_api_retrieve_unpackaged
        ):

            task = create_task(CheckComponents, {})

            with patch("builtins.open", mock_open(read_data="<Package></Package>")):

                response_messages = task._get_api_object_responce(
                    package_xml_path, version
                )

                assert response_messages is not None
                assert len(response_messages) == 1
                message_text = response_messages[
                    0
                ].firstChild.nextSibling.firstChild.nodeValue
                assert (
                    "Entity of type 'ApexClass' named 'Delivery' cannot be found"
                    in message_text
                ), f"{message_text}"

from unittest.mock import ANY, MagicMock, Mock, mock_open, patch

import pytest

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.check_components import CheckComponents
from cumulusci.tests.util import create_project_config

from .util import create_task


class TestCheckComponents:
    @patch("os.path.exists", return_value=True)
    @patch("os.remove")
    @patch("os.path.isdir", return_value=True)
    @patch("os.listdir", return_value=["package.xml"])
    @patch("os.path.join", side_effect=lambda *args: "/".join(args))
    @patch("cumulusci.core.sfdx.convert_sfdx_source")
    @patch(
        "cumulusci.tasks.salesforce.check_components.CheckComponents._is_plan",
        return_value=False,
    )
    @patch(
        "cumulusci.tasks.salesforce.check_components.CheckComponents._freeze_steps",
        return_value=[],
    )
    @patch(
        "cumulusci.tasks.salesforce.check_components.CheckComponents._collect_components_from_paths",
        return_value=[{"Type1": ["Comp1"]}, []],
    )
    @patch(
        "cumulusci.tasks.salesforce.check_components.CheckComponents._get_api_object_responce",
        return_value=[],
    )
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
    @patch(
        "cumulusci.utils.xml.metadata_tree.parse_package_xml_types",
        return_value={"Type2": ["Comp2"]},
    )
    def test_get_repo_existing_components(
        self,
        mock_metadata_parse,
        mock_open_file,
        mock_convert_sfdx_source,
        mock_path_join,
        mock_listdir,
        mock_isdir,
        mock_remove,
        mock_path_exists,
        mock_is_plan,
        mock_freeze_steps,
        mock_get_api_object,
        mock_parse,
        mock_collect_components,
    ):
        org_config = Mock(scratch=True, config={})
        org_config.username = "test_user"
        org_config.org_id = "test_org_id"
        self.org_config = Mock(return_value=("test", org_config))
        project_config = create_project_config()
        flow_config = {
            "test": {
                "steps": {
                    1: {
                        "flow": "test2",
                    }
                }
            },
            "test2": {
                "steps": {
                    1: {
                        "task": "deploy",
                        "options": {"path": "force-app/main/default"},
                    }
                }
            },
        }
        plan_config = {
            "title": "Test Install",
            "slug": "install",
            "tier": "primary",
            "steps": {1: {"flow": "test"}},
        }
        project_config.config["plans"] = {
            "Test Install": plan_config,
        }
        project_config.config["flows"] = flow_config

        task = create_task(CheckComponents, {"name": "test2"})
        task.deploy_paths = ["test"]

        (components, response_messages) = task.get_repo_existing_components("test2")
        assert "Type1" in components
        assert "Type2" in components
        assert "Comp1" in components["Type1"]
        assert "Comp2" in components["Type2"]

    @patch("os.path.exists", return_value=True)
    @patch("os.remove")
    @patch("os.path.isdir", return_value=True)
    @patch("os.listdir", return_value=["package.xml"])
    @patch("os.path.join", side_effect=lambda *args: "/".join(args))
    @patch("cumulusci.core.sfdx.convert_sfdx_source")
    @patch(
        "cumulusci.tasks.salesforce.check_components.CheckComponents._is_plan",
        return_value=False,
    )
    @patch(
        "cumulusci.tasks.salesforce.check_components.CheckComponents._freeze_steps",
        return_value=[],
    )
    @patch(
        "cumulusci.tasks.salesforce.check_components.CheckComponents._collect_components_from_paths",
        return_value=[{"Type1": ["Comp1"]}, []],
    )
    @patch(
        "cumulusci.tasks.salesforce.check_components.CheckComponents._get_api_object_responce",
        return_value=[],
    )
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
    @patch(
        "cumulusci.utils.xml.metadata_tree.parse_package_xml_types",
        return_value={"Type2": ["Comp2"]},
    )
    def test_get_repo_existing_components_paths_paramter(
        self,
        mock_metadata_parse,
        mock_open_file,
        mock_convert_sfdx_source,
        mock_path_join,
        mock_listdir,
        mock_isdir,
        mock_remove,
        mock_path_exists,
        mock_is_plan,
        mock_freeze_steps,
        mock_get_api_object,
        mock_parse,
        mock_collect_components,
    ):
        org_config = Mock(scratch=True, config={})
        org_config.username = "test_user"
        org_config.org_id = "test_org_id"
        self.org_config = Mock(return_value=("test", org_config))
        project_config = create_project_config()
        flow_config = {
            "test": {
                "steps": {
                    1: {
                        "flow": "test2",
                    }
                }
            },
            "test2": {
                "steps": {
                    1: {
                        "task": "deploy",
                        "options": {"path": "force-app/main/default"},
                    }
                }
            },
        }
        plan_config = {
            "title": "Test Install",
            "slug": "install",
            "tier": "primary",
            "steps": {1: {"flow": "test"}},
        }
        project_config.config["plans"] = {
            "Test Install": plan_config,
        }
        project_config.config["flows"] = flow_config

        task = create_task(CheckComponents, {"name": "test2"})
        task.deploy_paths = ["test"]

        (components, response_messages) = task.get_repo_existing_components("", "src")
        assert "Type1" in components
        assert "Type2" in components
        assert "Comp1" in components["Type1"]
        assert "Comp2" in components["Type2"]

    @patch("os.path.exists", return_value=True)
    @patch("os.remove")
    @patch("os.path.isdir", return_value=True)
    @patch("os.listdir", return_value=["some_file_or_directory"])
    @patch("os.path.join", side_effect=lambda *args: "/".join(args))
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
        mock_remove,
        mock_path_exists,
    ):
        mock_path_exists.return_value = True
        mock_isdir.return_value = True
        mock_listdir.return_value = ["some_file_or_directory"]
        mock_path_join.side_effect = lambda *args: "/".join(args)
        mock_convert_sfdx_source.return_value.__enter__.return_value = "/converted/path"

        mock_tree = MagicMock()
        mock_tree.findall.return_value = [
            MagicMock(
                findall=lambda tag: [MagicMock(text="Delivery")]
                if tag == "members"
                else [],
                find=lambda tag: MagicMock(text="ApexClass") if tag == "name" else None,
            ),
            MagicMock(
                findall=lambda tag: [MagicMock(text="Delivery__c")]
                if tag == "members"
                else [],
                find=lambda tag: MagicMock(text="CustomObject")
                if tag == "name"
                else None,
            ),
        ]
        mock_tree.find.return_value = MagicMock(text="58.0")
        mock_metadata_parse.return_value = mock_tree

        response_messages = [
            MagicMock(
                getElementsByTagName=MagicMock(
                    return_value=[
                        MagicMock(
                            firstChild=MagicMock(
                                nodeValue="Entity of type 'ApexClass' named 'CustomHealth' is cannot be found"
                            )
                        )
                    ]
                )
            )
        ]

        with patch("cumulusci.core.sfdx.sfdx") as sfdx:
            with patch.object(
                CheckComponents, "_get_api_object_responce"
            ) as mock_get_api_response:
                mock_get_api_response.return_value = response_messages
                task = create_task(CheckComponents, {"paths": "force-app/main/default"})
                components, api_response = task._collect_components_from_paths(
                    "force-app/main/default"
                )

                assert components is not None
                assert "ApexClass" not in components
        sfdx.assert_called_once_with(
            "project convert source",
            args=["-d", ANY, "-r", "force-app/main/default"],
            capture_output=True,
            check_return=True,
        )

    @patch("os.path.exists", return_value=False)
    def test_collect_components_from_nonexistent_paths(self, mock_path_exists):
        task = create_task(CheckComponents, {"paths": "invalid/path"})
        components, api_response = task._collect_components_from_paths("invalid/path")
        assert components is None
        assert api_response is None

    @patch("os.path.exists", return_value=False)
    def test_copy_to_tempdir_nonexistent_src(self, mock_exists):
        task = create_task(CheckComponents, {"paths": "force-app/main/default"})
        with pytest.raises(FileNotFoundError):
            task._copy_to_tempdir("nonexistent_src", "temp_dir")

    @patch("shutil.copy2")
    @patch("os.listdir", return_value=["file1", "file2"])
    @patch("os.path.isdir", return_value=False)
    @patch("os.path.exists", return_value=False)
    def test_copy_to_tempdir(self, mock_exists, mock_isdir, mock_listdir, mock_copy2):
        task = create_task(CheckComponents, {"paths": "force-app/main/default"})
        task._copy_to_tempdir("force-app/main/default", "temp_dir")
        mock_copy2.assert_called()

    def test_get_deployable_paths(self):
        task = create_task(CheckComponents, {"paths": "force-app/main/default"})
        tasks = [
            {
                "task_config": {
                    "options": {
                        "path": "unpackaged/pre",
                        "subfolder": "/unpackaged/post/test",
                    }
                }
            },
            {"task_config": {"options": {"path": "force-app"}}},
        ]
        paths = task._get_deployable_paths(tasks)
        assert paths == ["unpackaged/pre", "/unpackaged/post/test", "force-app"]

    def test_is_plan_valid(self):
        task = create_task(CheckComponents, {"paths": "force-app/main/default"})
        with patch.object(task.project_config, "lookup") as mock_lookup:
            mock_lookup.side_effect = lambda name: {
                "plans__test_plan": True,
                "flows__test_flow": False,
            }.get(name, None)
            assert task._is_plan("test_plan") is True
            assert task._is_plan("test_flow") is False

    def test_is_plan_invalid(self):
        task = create_task(CheckComponents, {"name": "invalid_name"})
        with patch.object(task.project_config, "lookup", return_value=None):
            with pytest.raises(
                TaskOptionsError,
                match="No paths provided and unable to determine the current plan or flow name.",
            ):
                task._is_plan("invalid_name")

    def test_init_options_with_both_paths_and_name(self):
        with pytest.raises(
            TaskOptionsError, match="Please provide either --paths or --name"
        ):
            create_task(CheckComponents, {"paths": "some/path", "name": "some_plan"})

    def test_init_options_with_neither_paths_nor_name(self):
        with pytest.raises(
            TaskOptionsError,
            match="This task requires a plan/flow name or paths options. Pass --paths or --name options",
        ):
            create_task(CheckComponents, {})

    def test_load_deploy_paths(self):
        task = create_task(CheckComponents, {"name": "some_name"})
        with patch.object(
            task,
            "_get_plan_tasks",
            return_value=[{"task_config": {"options": {"path": "unpackaged/pre"}}}],
        ):
            with patch.object(
                task, "_get_deployable_paths", return_value=["unpackaged/pre"]
            ):
                task._load_deploy_paths("some_name", is_plan=True)
                assert task.deploy_paths == ["unpackaged/pre"]

    def test_freeze_steps__skip(self):
        project_config = create_project_config()
        plan_config = {
            "title": "Test Install",
            "slug": "install",
            "tier": "primary",
            "steps": {1: {"task": "None"}},
        }
        project_config.config["plans"] = {
            "Test Install": plan_config,
        }
        task_config = TaskConfig({"options": {"name": "Test Install"}})
        task = CheckComponents(project_config, task_config)
        steps = task._freeze_steps(project_config, plan_config)
        assert steps == []

    def test_freeze_steps_nested(self):
        project_config = create_project_config()
        flow_config = {
            "test": {
                "steps": {
                    1: {
                        "flow": "test2",
                    }
                }
            },
            "test2": {
                "steps": {
                    1: {
                        "task": "deploy",
                        "options": {"path": "force-app/main/default"},
                    }
                }
            },
        }
        plan_config = {
            "title": "Test Install",
            "slug": "install",
            "tier": "primary",
            "steps": {1: {"flow": "test"}},
        }
        project_config.config["plans"] = {
            "Test Install": plan_config,
        }
        project_config.config["flows"] = flow_config

        task_config = TaskConfig({"options": {"name": "Test Install"}})
        task = CheckComponents(project_config, task_config)
        steps = task._freeze_steps(project_config, plan_config)
        assert steps[0]["name"] == "deploy"
        assert len(steps) == 1

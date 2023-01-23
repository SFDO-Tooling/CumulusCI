from unittest import mock

import click
import pytest

from cumulusci.cli.runtime import CliRuntime
from cumulusci.core.config import FlowConfig
from cumulusci.core.exceptions import CumulusCIException, FlowNotFoundError
from cumulusci.core.flowrunner import FlowCoordinator

from .. import flow
from .utils import DummyTask, run_click_command


@mock.patch("cumulusci.cli.flow.CliTable")
def test_flow_list(cli_tbl):
    runtime = mock.Mock()
    runtime.get_available_flows.return_value = [
        {"name": "test_flow", "description": "Test Flow", "group": "Testing"}
    ]
    runtime.universal_config.cli__plain_output = None
    run_click_command(flow.flow_list, runtime=runtime, plain=False, print_json=False)

    cli_tbl.assert_called_with(
        [["Flow", "Description"], ["test_flow", "Test Flow"]],
        "Testing",
    )


@mock.patch("json.dumps")
def test_flow_list_json(json_):
    flows = [{"name": "test_flow", "description": "Test Flow"}]
    runtime = mock.Mock()
    runtime.get_available_flows.return_value = flows
    runtime.universal_config.cli__plain_output = None

    run_click_command(flow.flow_list, runtime=runtime, plain=False, print_json=True)

    json_.assert_called_with(flows)


@mock.patch("click.echo")
def test_flow_info(echo):

    runtime = CliRuntime(
        config={
            "flows": {
                "test": {
                    "steps": {
                        1: {
                            "task": "test_task",
                            "options": {"option_name": "option_value"},
                        }
                    }
                }
            },
            "tasks": {
                "test_task": {
                    "class_path": "cumulusci.cli.tests.test_flow.DummyTask",
                    "description": "Test Task",
                }
            },
        },
        load_keychain=False,
    )

    run_click_command(flow.flow_info, runtime=runtime, flow_name="test")

    echo.assert_called_with(
        "\nFlow Steps\n1) task: test_task [from current folder]\n   options:\n       option_name: option_value"
    )


def test_flow_info__not_found():
    runtime = mock.Mock()
    runtime.get_flow.side_effect = FlowNotFoundError
    with pytest.raises(click.UsageError):
        run_click_command(flow.flow_info, runtime=runtime, flow_name="test")


@mock.patch("cumulusci.cli.flow.group_items")
@mock.patch("cumulusci.cli.flow.document_flow")
def test_flow_doc__no_flows_rst_file(doc_flow, group_items):
    runtime = mock.Mock()
    runtime.universal_config.flows = {"test": {}}
    flow_config = FlowConfig({"description": "Test Flow", "steps": {}})
    runtime.get_flow.return_value = FlowCoordinator(None, flow_config)

    group_items.return_value = {"Group One": [["test flow", "description"]]}

    run_click_command(flow.flow_doc, runtime=runtime)
    group_items.assert_called_once()
    doc_flow.assert_called()


@mock.patch("click.echo")
@mock.patch("cumulusci.cli.flow.load_yaml_data")
def test_flow_doc__with_flows_rst_file(load_yaml_data, echo):
    runtime = CliRuntime(
        config={
            "flows": {
                "Flow1": {
                    "steps": {},
                    "description": "Description of Flow1",
                    "group": "Group1",
                }
            }
        },
    )

    load_yaml_data.return_value = {
        "intro_blurb": "opening blurb for flow reference doc",
        "groups": {
            "Group1": {"description": "This is a description of group1."},
        },
        "flows": {"Flow1": {"rst_text": "Some ``extra`` **pizzaz**!"}},
    }

    run_click_command(flow.flow_doc, runtime=runtime, project=True)

    assert 1 == load_yaml_data.call_count

    expected_call_args = [
        "Flow Reference\n==========================================\n\nopening blurb for flow reference doc\n\n",
        "Group1\n------",
        "This is a description of group1.",
        ".. _Flow1:\n\nFlow1\n^^^^^\n\n**Description:** Description of Flow1\n\nSome ``extra`` **pizzaz**!\n**Flow Steps**\n\n.. code-block:: console\n",
        "",
    ]
    expected_call_args = [mock.call(s) for s in expected_call_args]
    assert echo.call_args_list == expected_call_args


def test_flow_run():
    org_config = mock.Mock(scratch=True, config={})
    runtime = CliRuntime(
        config={
            "flows": {"test": {"steps": {1: {"task": "test_task"}}}},
            "tasks": {
                "test_task": {
                    "class_path": "cumulusci.cli.tests.test_flow.DummyTask",
                    "description": "Test Task",
                }
            },
        },
        load_keychain=False,
    )
    runtime.get_org = mock.Mock(return_value=("test", org_config))
    runtime.get_flow = mock.Mock()

    run_click_command(
        flow.flow_run,
        runtime=runtime,
        flow_name="test",
        org="test",
        delete_org=True,
        debug=False,
        o=[("test_task__color", "blue")],
        no_prompt=True,
    )

    runtime.get_flow.assert_called_once_with(
        "test", options={"test_task": {"color": "blue"}}
    )
    org_config.delete_org.assert_called_once()


def test_flow_run__delete_org_when_error_occurs_in_flow():
    org_config = mock.Mock(scratch=True, config={})
    runtime = CliRuntime(
        config={
            "flows": {"test": {"steps": {1: {"task": "test_task"}}}},
            "tasks": {
                "test_task": {
                    "class_path": "cumulusci.cli.tests.test_flow.DummyTask",
                    "description": "Test Task",
                }
            },
        },
        load_keychain=False,
    )
    runtime.get_org = mock.Mock(return_value=("test", org_config))
    coordinator = mock.Mock()
    coordinator.run.side_effect = CumulusCIException
    runtime.get_flow = mock.Mock(return_value=coordinator)

    with pytest.raises(CumulusCIException):
        run_click_command(
            flow.flow_run,
            runtime=runtime,
            flow_name="test",
            org="test",
            delete_org=True,
            debug=False,
            o=[("test_task__color", "blue")],
            no_prompt=True,
        )

    runtime.get_flow.assert_called_once_with(
        "test", options={"test_task": {"color": "blue"}}
    )
    org_config.delete_org.assert_called_once()


def test_flow_run__option_error():
    org_config = mock.Mock(scratch=True, config={})
    runtime = CliRuntime(config={"noop": {}}, load_keychain=False)
    runtime.get_org = mock.Mock(return_value=("test", org_config))

    with pytest.raises(click.UsageError, match="-o"):
        run_click_command(
            flow.flow_run,
            runtime=runtime,
            flow_name="test",
            org="test",
            delete_org=True,
            debug=False,
            o=[("test_task", "blue")],
            no_prompt=True,
        )


def test_flow_run__delete_non_scratch():
    org_config = mock.Mock(scratch=False)
    runtime = mock.Mock()
    runtime.get_org.return_value = ("test", org_config)

    with pytest.raises(click.UsageError):
        run_click_command(
            flow.flow_run,
            runtime=runtime,
            flow_name="test",
            org="test",
            delete_org=True,
            debug=False,
            o=None,
            no_prompt=True,
        )


@mock.patch("click.echo")
def test_flow_run__org_delete_error(echo):
    org_config = mock.Mock(scratch=True, config={})
    org_config.delete_org.side_effect = Exception
    org_config.save_if_changed.return_value.__enter__ = lambda *args: ...
    org_config.save_if_changed.return_value.__exit__ = lambda *args: ...
    runtime = CliRuntime(
        config={
            "flows": {"test": {"steps": {1: {"task": "test_task"}}}},
            "tasks": {
                "test_task": {
                    "class_path": "cumulusci.cli.tests.test_flow.DummyTask",
                    "description": "Test Task",
                }
            },
        },
        load_keychain=False,
    )
    runtime.get_org = mock.Mock(return_value=("test", org_config))
    DummyTask._run_task = mock.Mock()

    kwargs = {
        "runtime": runtime,
        "flow_name": "test",
        "org": "test",
        "delete_org": True,
        "debug": False,
        "no_prompt": True,
        "o": (("test_task__color", "blue"),),
    }

    run_click_command(flow.flow_run, **kwargs)

    echo.assert_any_call(
        "Scratch org deletion failed.  Ignoring the error below to complete the flow:"
    )

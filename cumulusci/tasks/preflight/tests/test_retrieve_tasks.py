from unittest import mock

import pytest

from cumulusci.cli.runtime import CliRuntime
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.preflight.retrieve_tasks import RetrieveTasks
from cumulusci.tasks.salesforce.tests.util import create_task


class TestRetrieveTasks:
    @pytest.mark.parametrize(
        "available_tasks, group_name, expected_output",
        [
            (
                [
                    {
                        "name": "test_task1",
                        "description": "Test Task",
                        "group": "Group",
                    },
                    {
                        "name": "test_task2",
                        "description": "Test Task",
                        "group": "Group",
                    },
                    {
                        "name": "test_task3",
                        "description": "Test Task",
                        "group": "Test Group",
                    },
                ],
                "Group",
                ["test_task1", "test_task2"],
            ),
            (
                [
                    {
                        "name": "test_task1",
                        "description": "Test Task",
                        "group": "Group",
                    },
                ],
                "Tests",
                None,
            ),
        ],
    )
    def test_run_task(self, available_tasks, group_name, expected_output):
        task = create_task(RetrieveTasks, options={"group_name": group_name})

        with mock.patch.object(
            CliRuntime, "get_available_tasks", return_value=available_tasks
        ):
            if expected_output is not None:
                output = task()
                assert output == expected_output
            else:
                with pytest.raises(
                    CumulusCIException, match="No tasks in the specified group"
                ):
                    task()

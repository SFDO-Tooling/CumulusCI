from unittest.mock import Mock, call

import pytest

from cumulusci.core.exceptions import CumulusCIException, SalesforceException
from cumulusci.tasks.salesforce.network_member_group import CreateNetworkMemberGroups
from cumulusci.tasks.salesforce.tests.util import create_task


class TestCreateNetworkMemberGroups:
    """
    Unit tests cumulusci.tasks.salesforce.network_member_group.CreateNetworkMemberGroups.
    """

    def test_get_network_id__no_network_found(self):
        network_name = "network_name"

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        task.sf = Mock()
        task.sf.query_all.Mock()
        task.sf.query_all.return_value = {"records": []}
        task.format_soql = Mock()

        # Execute the test.
        with pytest.raises(SalesforceException) as context:
            task._get_network_id(network_name)

        # Assert scenario execute as expected.
        assert (
            f'No Network record found with Name "{network_name}"'
            == context.value.args[0]
        )

        task.sf.query_all.assert_called_once_with(
            f"SELECT Id FROM Network WHERE Name = '{network_name}' LIMIT 1"
        )

    def test_get_network_id__network_found(self):
        network_name = "network_name"

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        task.sf = Mock()
        task.sf.query_all.return_value = {"records": [{"Id": "NetworkId"}]}
        task.format_soql = Mock()

        expected = task.sf.query_all.return_value["records"][0]["Id"]

        # Execute the test.
        actual = task._get_network_id(network_name)

        # Assert scenario execute as expected.
        assert expected == actual

        task.sf.query_all.assert_called_once_with(
            f"SELECT Id FROM Network WHERE Name = '{network_name}' LIMIT 1"
        )

    def test_get_network_member_group_parent_ids(self):
        network_name = "network_name"
        network_id = "network_id"

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        task.sf = Mock()
        task.sf.query_all.return_value = {
            "records": [
                {"ParentId": "0"},
                {"ParentId": "2"},
                {"ParentId": "3"},
                {"ParentId": "1"},
            ]
        }

        expected = set(["0", "1", "2", "3"])

        # Execute the test.
        actual = task._get_network_member_group_parent_ids(network_id)

        # Assert scenario execute as expected.
        assert expected == actual

        task.sf.query_all.assert_called_once_with(
            f"SELECT ParentId FROM NetworkMemberGroup WHERE NetworkId = '{network_id}'"
        )

    def test_get_parent_ids_by_name(self):
        network_name = "network_name"
        sobject_type = "sobject_type"
        record_names = [
            "Name_0",
            "Name_1",
            "Name_2",
        ]

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        task.sf = Mock()
        task.sf.query_all = Mock(
            return_value={
                "records": [
                    {"Name": "Name_0", "Id": "Id_0"},
                    {"Name": "Name_2", "Id": "Id_2"},
                ]
            }
        )

        expected = {
            "Name_0": "Id_0",
            "Name_1": None,
            "Name_2": "Id_2",
        }

        # Execute the test.
        actual = task._get_parent_ids_by_name(sobject_type, record_names)

        # Assert scenario execute as expected.
        assert expected == actual

        task.sf.query_all.assert_called_once_with(
            "SELECT Id, Name FROM {} WHERE Name IN ('{}')".format(
                sobject_type,
                "','".join(record_names),
            )
        )

    def test_get_parent_ids_by_label(self):
        network_name = "network_name"
        sobject_type = "PermissionSet"
        record_names = [
            "Name_0",
            "Name_1",
            "Name_2",
        ]

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        task.sf = Mock()
        task.sf.query_all.return_value = {
            "records": [
                {"Label": "Name_0", "Id": "Id_0"},
                {"Label": "Name_2", "Id": "Id_2"},
            ]
        }

        expected = {
            "Name_0": "Id_0",
            "Name_1": None,
            "Name_2": "Id_2",
        }

        # Execute the test.
        actual = task._get_parent_ids_by_name(sobject_type, record_names)

        # Assert scenario execute as expected.
        assert expected == actual

        task.sf.query_all.assert_called_once_with(
            "SELECT Id, Label FROM {} WHERE Label IN ('{}')".format(
                sobject_type,
                "','".join(record_names),
            )
        )

    def test_process_parent__no_names(self):
        network_name = "network_name"
        sobject_type = "sobject_type"
        for record_names in [
            None,
            [],
        ]:

            task = create_task(
                CreateNetworkMemberGroups, {"network_name": network_name}
            )

            parent_ids_by_name = Mock()

            task._get_parent_ids_by_name = Mock(return_value=parent_ids_by_name)

            task._create_network_member_group = Mock()

            # Execute the test.
            task._process_parent(sobject_type, record_names)

            # Assert scenario execute as expected.

            task._get_parent_ids_by_name.assert_not_called()

            parent_ids_by_name.items.assert_not_called()

            task._create_network_member_group.assert_not_called()

    def test_process_parent__with_names(self):
        network_name = "network_name"
        sobject_type = "sobject_type"
        record_names = [
            "Name_0",
            "Name_1",
            "Name_2",
        ]

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        parent_ids_by_name = Mock()
        parent_ids_by_name.items.return_value = [
            ("Name_0", "Id_0"),
            ("Name_1", None),
            ("Name_2", "Id_2"),
        ]

        task._get_parent_ids_by_name = Mock(return_value=parent_ids_by_name)

        task._create_network_member_group = Mock()

        expected_create_network_member_group_calls = []
        for parent_name, parent_id in parent_ids_by_name.items.return_value:
            expected_create_network_member_group_calls.append(
                call(sobject_type, parent_name, parent_id)
            )

        # Execute the test.
        task._process_parent(sobject_type, record_names)

        # Assert scenario execute as expected.

        task._get_parent_ids_by_name.assert_called_once_with(sobject_type, record_names)

        parent_ids_by_name.items.assert_called_once_with()

        task._create_network_member_group.assert_has_calls(
            expected_create_network_member_group_calls
        )

    def test_create_network_member_group__parent_not_found_in_query(self):
        network_name = "network_name"
        sobject_type = "sobject_type"
        parent_name = "parent_name"
        parent_id = None

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        task._parent_ids = set()

        task._network_id = "network_id"

        task.sf = Mock()

        insert_response = Mock()
        task.sf.NetworkMemberGroup.create = Mock(insert_response)

        # Execute the test.
        with pytest.raises(CumulusCIException) as context:
            task._create_network_member_group(sobject_type, parent_name, parent_id)

        # Assert scenario execute as expected.
        assert (
            f'No {sobject_type} record found with Name "{parent_name}"'
            == context.value.args[0]
        )

        task.sf.NetworkMemberGroup.create.assert_not_called()

    def test_create_network_member_group__parent_already_exists(self):
        network_name = "network_name"
        sobject_type = "sobject_type"
        parent_name = "parent_name"
        parent_id = "parent_id"

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        task._parent_ids = set()
        task._parent_ids.add(parent_id)

        task._network_id = "network_id"

        task.sf = Mock()
        task.sf.NetworkMemberGroup = Mock()

        insert_response = Mock()
        insert_response.get = Mock()
        task.sf.NetworkMemberGroup.create = Mock(insert_response)

        # Execute the test.
        task._create_network_member_group(sobject_type, parent_name, parent_id)

        task.sf.NetworkMemberGroup.create.assert_not_called()

    def test_create_network_member_group__creating_parent_with_success(self):
        network_name = "network_name"
        sobject_type = "sobject_type"
        parent_name = "parent_name"
        parent_id = "parent_id"

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        task._parent_ids = set()

        task._network_id = "network_id"

        task.sf = Mock()
        task.sf.NetworkMemberGroup = Mock()

        insert_response = {"success": True}

        task.sf.NetworkMemberGroup.create.return_value = insert_response

        # Execute the test.
        task._create_network_member_group(sobject_type, parent_name, parent_id)

        task.sf.NetworkMemberGroup.create.assert_called_once_with(
            {"NetworkId": task._network_id, "ParentId": parent_id}
        )

    def test_create_network_member_group__creating_parent_not_success__with_errors(
        self,
    ):
        network_name = "network_name"
        sobject_type = "sobject_type"
        parent_name = "parent_name"
        parent_id = "parent_id"

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        task._parent_ids = set()

        task._network_id = "network_id"

        task.sf = Mock()

        errors = ["error_0", "error_1"]
        insert_response = {"success": False, "errors": errors}

        task.sf.NetworkMemberGroup.create.return_value = insert_response

        # Execute the test.
        with pytest.raises(SalesforceException) as context:
            task._create_network_member_group(sobject_type, parent_name, parent_id)

        # Assert scenario execute as expected.
        assert (
            f'Error creating NetworkMemberGroup for Network "{task._network_id}" for parent {sobject_type} "{parent_name}" {parent_id}.   Errors: {", ".join(errors)}'
            == context.value.args[0]
        )

        task.sf.NetworkMemberGroup.create.assert_called_once_with(
            {"NetworkId": task._network_id, "ParentId": parent_id}
        )

    def test_create_network_member_group__creating_parent_not_success__no_errors(
        self,
    ):
        network_name = "network_name"
        sobject_type = "sobject_type"
        parent_name = "parent_name"
        parent_id = "parent_id"

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        task._parent_ids = set()

        task._network_id = "network_id"

        task.sf = Mock()

        insert_response = {"success": False, "errors": None}

        task.sf.NetworkMemberGroup.create = Mock(return_value=insert_response)

        # Execute the test.
        with pytest.raises(SalesforceException) as e:
            task._create_network_member_group(sobject_type, parent_name, parent_id)

        # Assert scenario execute as expected.
        assert (
            f'Error creating NetworkMemberGroup for Network "{task._network_id}" for parent {sobject_type} "{parent_name}" {parent_id}.   Errors: {", ".join([])}'
            == e.value.args[0]
        )

        task.sf.NetworkMemberGroup.create.assert_called_once_with(
            {"NetworkId": task._network_id, "ParentId": parent_id}
        )

    def test_run_task__none_profile_names_and_permission_set_names(
        self,
    ):
        network_name = "network_name"

        task = create_task(CreateNetworkMemberGroups, {"network_name": network_name})

        task._get_network_id = Mock(return_value="network_id")
        task._get_network_member_group_parent_ids = Mock(return_value=set(["Id_1"]))

        task._process_parent = Mock()
        expected_process_parent_calls = [
            call("Profile", []),
            call("PermissionSet", []),
        ]

        # Execute the test.
        task._run_task()

        # Assert scenario execute as expected.
        task._get_network_id.assert_called_once_with(task.options.get("network_name"))

        task._get_network_member_group_parent_ids.assert_called_once_with(
            task._get_network_id.return_value
        )

        task._process_parent.assert_has_calls(expected_process_parent_calls)

    def test_run_task__string_profile_names_and_permission_set_names(
        self,
    ):
        network_name = "network_name"
        profile_names = "profile_name"
        permission_set_names = "permission_set_name"

        task = create_task(
            CreateNetworkMemberGroups,
            {
                "network_name": network_name,
                "profile_names": profile_names,
                "permission_set_names": permission_set_names,
            },
        )

        task._get_network_id = Mock(return_value="network_id")
        task._get_network_member_group_parent_ids = Mock(return_value=set(["Id_1"]))
        task._process_parent = Mock()
        expected_process_parent_calls = [
            call("Profile", [profile_names]),
            call("PermissionSet", [permission_set_names]),
        ]

        # Execute the test.
        task._run_task()

        # Assert scenario execute as expected.
        task._get_network_id.assert_called_once_with(task.options.get("network_name"))

        task._get_network_member_group_parent_ids.assert_called_once_with(
            task._get_network_id.return_value
        )

        task._process_parent.assert_has_calls(expected_process_parent_calls)

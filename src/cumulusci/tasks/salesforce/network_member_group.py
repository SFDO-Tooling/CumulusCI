from typing import List

from simple_salesforce import format_soql

from cumulusci.core.exceptions import CumulusCIException, SalesforceException
from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class CreateNetworkMemberGroups(BaseSalesforceApiTask):
    """
    Creates NetworkMemberGroup for a Network (Experience Site) for Profiles and Permission Sets
    that don't already have a corresponding NetworkMemberGroup.

    Raises exceptions if records cannot be found:
    - Network with Name network_name
    - Profiles with Names in profile_names
    - Permission Sets with Names in permission_set_names
    """

    task_options = {
        "network_name": {
            "description": (
                "Name of Network to add NetworkMemberGroup children records."
            ),
            "required": True,
        },
        "profile_names": {
            "description": (
                "List of Profile Names to add as NetworkMemberGroups "
                "for this Network."
            ),
            "required": False,
        },
        "permission_set_names": {
            "description": (
                "List of PermissionSet Names to add as NetworkMemberGroups "
                "for this Network."
            ),
            "required": False,
        },
    }

    def _get_network_id(self, network_name: str) -> str:
        """
        Returns Id of Network record with Name network_name.
        Raises a SalesforceException if no Network is found.
        """

        networks = self.sf.query_all(
            format_soql(
                "SELECT Id FROM Network WHERE Name = {network_name} LIMIT 1",
                network_name=network_name,
            )
        )

        if not networks["records"]:
            raise SalesforceException(
                f'No Network record found with Name "{network_name}"'
            )
        self.logger.info(
            f"Creating NetworkMemberGroup records for {network_name} Network:"
        )
        return networks["records"][0]["Id"]

    def _get_network_member_group_parent_ids(self, network_id) -> set:
        """
        Collect existing NetworkMemberGroup Parent IDs (associated Profile or Permission Set ID).
        An excpetion is thrown trying to create a NetworkMemberGroup for a parent who already has a
        record.
        """

        network_member_group_parent_ids = set()
        for record in self.sf.query_all(
            f"SELECT ParentId FROM NetworkMemberGroup WHERE NetworkId = '{network_id}'"  # noqa: E501
        )["records"]:
            network_member_group_parent_ids.add(record["ParentId"])
        return network_member_group_parent_ids

    def _get_parent_ids_by_name(self, sobject_type: str, record_names: List[str]):
        """
        Returns a Dict: Name --> ID of records with Name in record_names for
        sObject_type.   Dict value are None for all record_names that do not
        have corresponding records.
        """
        parent_ids_by_name = dict((name, None) for name in record_names)

        if sobject_type == "PermissionSet":
            field_key = "Label"
        else:
            field_key = "Name"

        for record in self.sf.query_all(
            "SELECT Id, {} FROM {} WHERE {} IN ('{}')".format(
                field_key,
                sobject_type,
                field_key,
                "','".join(record_names),
            )
        )["records"]:
            record_name = record[field_key]
            parent_ids_by_name[record_name] = record["Id"]

        return parent_ids_by_name

    def _process_parent(self, sobject_type, record_names) -> None:
        """
        For a specific sobject_type and record_names, queries all Salesforce IDs
        corresponding to records of SObjectType sobject_type with Name in
        record_names.   Then, tries to create NetworkMemberGroup for each
        parent in record_names.
        """

        if not record_names:
            return

        self.logger.info(f"    {sobject_type}:")

        # Collect Parent IDs by Name.
        parent_ids_by_name = self._get_parent_ids_by_name(sobject_type, record_names)

        # Create NetworkMemberGroup records.
        for parent_name, parent_id in parent_ids_by_name.items():
            self._create_network_member_group(sobject_type, parent_name, parent_id)

    def _create_network_member_group(
        self, sobject_type, parent_name, parent_id
    ) -> None:
        """
        Processes and logs creating a NetworkMemberGroup for a specific parent.

        Outcomes:
        - Raises a CumulusCIException if record_id is None meaning
          no corresponding record was found in _get_parent_ids_by_name.
        - Logs a warning that a NetworkMemberGroup already exists is parent_id
          is in self._parent_ids.
        - Creates a NetworkMemberGroup for parent_id and logs the result.
        """

        # Assert a Parent was found for each Name.
        if not parent_id:
            raise CumulusCIException(
                f'No {sobject_type} record found with Name "{parent_name}"'
            )
        # If the Profile/Permission set already exists for a NetworkMemberGroup -
        if parent_id in self._parent_ids:
            self.logger.warning(f'        Already exists for "{parent_name}"')
        else:
            insert_response = self.sf.NetworkMemberGroup.create(
                {"NetworkId": self._network_id, "ParentId": parent_id}
            )
            if insert_response.get("success") is True:
                self.logger.info(f'        "{parent_name}"')
            else:
                # It might be impossible to get to this state.
                # If there's a query exception, it gets thrown before this is called.
                raise SalesforceException(
                    f'Error creating NetworkMemberGroup for Network "{self._network_id}" for parent {sobject_type} "{parent_name}" {parent_id}.   Errors: {", ".join(insert_response.get("errors") or [])}'
                )

    def _run_task(self):
        """
        Gets required information then tries to create NetworkMemberGroups for
        Profiles and Permission Sets cooresponding to profile_names and
        permission_set_names respectively.
        """

        self._network_id = self._get_network_id(self.options["network_name"])
        self._parent_ids = self._get_network_member_group_parent_ids(self._network_id)

        # Create NetworkMemberGroup records.
        for sobject_type, record_names in {
            "Profile": process_list_arg(self.options.get("profile_names") or []),
            "PermissionSet": process_list_arg(
                self.options.get("permission_set_names") or []
            ),
        }.items():
            self._process_parent(sobject_type, record_names)

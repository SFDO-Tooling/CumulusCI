from cumulusci.tasks.preflight.retrieve_tasks import RetrieveTasks
from cumulusci.tasks.salesforce.tests.util import create_task


class TestRetrieveTasks:
    def test_run_task(self):
        expected_output = [
            "check_advanced_currency_management",
            "check_chatter_enabled",
            "check_enhanced_notes_enabled",
            "check_my_domain_active",
            "check_org_settings_value",
            "check_org_wide_defaults",
            "check_sobject_permissions",
            "check_sobjects_available",
            "get_assigned_permission_set_licenses",
            "get_assigned_permission_sets",
            "get_available_licenses",
            "get_available_permission_set_licenses",
            "get_available_permission_sets",
            "get_existing_record_types",
            "get_existing_sites",
            "get_installed_packages",
        ]
        task = create_task(
            RetrieveTasks, options={"group_name": "Salesforce Preflight Checks"}
        )
        output = task()
        assert output == expected_output

    def test_run_nogroup_name(self):
        expected_output = []
        task = create_task(RetrieveTasks, options={"group_name": "Temperorry checks"})
        output = task()
        assert output == expected_output

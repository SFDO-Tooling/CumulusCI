from cumulusci.core.utils import process_list_arg
from cumulusci.tasks.salesforce.BaseSalesforceApiTask import BaseSalesforceApiTask


class CreatePermissionSet(BaseSalesforceApiTask):
    task_options = {
        "api_name": {
            "description": "API name of generated Permission Set",
            "required": True,
        },
        "label": {"description": "Label of generated Permission Set"},
        "user_permissions": {
            "description": "List of User Permissions to include in the Permission Set.",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)

        self.options["user_permissions"] = process_list_arg(
            self.options["user_permissions"]
        )

    def _run_task(self):
        result = self.sf.PermissionSet.create(
            {
                "Name": self.options["api_name"],
                "Label": self.options.get("label") or self.options["api_name"],
                **{perm: True for perm in self.options["user_permissions"]},
            }
        )
        self.sf.PermissionSetAssignment.create(
            {"AssigneeId": self.org_config.user_id, "PermissionSetId": result["id"]}
        )

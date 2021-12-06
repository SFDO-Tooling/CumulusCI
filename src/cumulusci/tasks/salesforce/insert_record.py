from cumulusci.core.exceptions import SalesforceException
from cumulusci.core.utils import process_bool_arg, process_list_of_pairs_dict_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class InsertRecord(BaseSalesforceApiTask):
    task_docs = """
        For example:

        cci task run insert_record --org dev -o object PermissionSet -o values Name:HardDelete,PermissionsBulkApiHardDelete:true
    """

    task_options = {
        "object": {"description": "An sObject type to insert", "required": True},
        "values": {
            "description": "Field names and values in the format 'aa:bb,cc:dd', or a YAML dict in cumulusci.yml.",
            "required": True,
        },
        "tooling": {"description": "If True, use the Tooling API instead of REST API."},
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.values = process_list_of_pairs_dict_arg(self.options["values"])
        self.object = self.options["object"]
        self.use_tooling = process_bool_arg(self.options.get("tooling", False))

    def _run_task(self):
        api = self.sf if not self.use_tooling else self.tooling
        object_handler = getattr(api, self.object)

        rc = object_handler.create(self.values)
        if rc["success"]:
            self.logger.info(f"{self.object} record inserted: {rc['id']}")
        else:
            # this will probably never execute, due to simple_salesforce throwing
            # an exception, but just in case:
            raise SalesforceException(
                f"Could not insert {self.object} record : {rc['errors']}"
            )

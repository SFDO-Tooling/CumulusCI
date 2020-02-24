from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.utils import process_list_of_pairs_dict_arg
from cumulusci.core.exceptions import SalesforceException


class InsertRecord(BaseSalesforceApiTask):
    task_docs = """
        For example:

        cci task run insert_record --org dev -o object PermissionSet -o values Name:HardDelete,PermissionsBulkApiHardDelete:true
    """

    task_options = {
        "object": {"description": "An sObject type to insert", "required": True},
        "values": {
            "description": "Field names and values in the format 'aa:bb,cc:dd'",
            "required": True,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.values = process_list_of_pairs_dict_arg(self.options["values"])
        self.object = self.options["object"]

    def _run_task(self):
        object_handler = getattr(self.sf, self.object)
        rc = object_handler.create(self.values)
        if rc["success"]:
            self.logger.info(f"{self.object} record inserted: {rc['id']}")
        else:
            # this will probably never execute, due to simple_salesforce throwing
            # an exception, but just in case:
            raise SalesforceException(
                f"Could not insert {self.object} record : {rc['errors']}"
            )

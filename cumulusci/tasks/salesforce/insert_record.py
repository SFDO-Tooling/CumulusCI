from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.core.utils import process_list_of_pairs_dict_arg


class InsertRecord(BaseSalesforceApiTask):
    task_docs = """
        For example:

        cci task run insert_record --org dev -o object PermissionSet -o values Name:HardDelete,PermissionsBulkApiHardDelete:true
    """

    task_options = {
        "object": {"description": "An SObject type to insert", "required": True},
        "values": {
            "description": "Field names and values in the format 'aa:bb,cc:dd'",
            "required": True,
        },
    }

    def _run_task(self):
        object_handler = getattr(self.sf, self.options["object"])
        values = process_list_of_pairs_dict_arg(self.options["values"])
        rc = object_handler.create(values)
        self.logger.info(f"Record inserted {rc['id']}")

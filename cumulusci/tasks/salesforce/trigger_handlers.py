from collections import defaultdict
from contextlib import contextmanager

import yaml

from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.core.utils import process_bool_arg, process_list_arg
from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from cumulusci.utils.fileutils import FSResource, open_fs_resource


class SetTDTMHandlerStatus(BaseSalesforceApiTask):
    """Alter the active status of specific NPSP or EDA TDTM trigger handlers.
    Save a state file to allow the handlers to be restored to their previous status.
    """

    task_options = {
        "handlers": {
            "description": "List of Trigger Handlers (by Class, Object, or 'Class:Object') to affect (defaults to all handlers)."
        },
        "namespace": {
            "description": "The namespace of the Trigger Handler object ('eda' or 'npsp'). The task will apply the namespace if needed."
        },
        "active": {
            "description": "True or False to activate or deactivate trigger handlers."
        },
        "restore_file": {
            "description": "Path to the state file to store or restore the current trigger handler state. Set to False to discard trigger state information. By default the state is cached in an org-specific directory for later restore."
        },
        "restore": {
            "description": "If True, restore the state of Trigger Handlers to that stored in the (specified or default) restore file."
        },
    }
    should_restore = False
    should_save = False

    def _init_options(self, kwargs):
        super(SetTDTMHandlerStatus, self)._init_options(kwargs)
        self.options["handlers"] = process_list_arg(self.options.get("handlers", []))
        self.options["active"] = process_bool_arg(self.options.get("active") or False)
        has_restore_file = (
            self.options.get("restore_file") is not False
            and self.options.get("restore_file") != "False"
        )
        should_restore = process_bool_arg(self.options.get("restore", False))
        if should_restore:
            if not has_restore_file:
                raise TaskOptionsError("Restoring requires a restore file name")
            self.should_restore = True
        else:
            self.should_save = has_restore_file

    @contextmanager
    def _default_restore_resource(self):
        with self.org_config.get_orginfo_cache_dir(self.__module__) as cache:
            yield cache / "trigger_status.yml"

    def _run_task(self):
        restore_path = self.options.get("restore_file")
        if restore_path:
            restore_file = open_fs_resource(restore_path)
        else:
            restore_file = self._default_restore_resource()

        with restore_file as f:
            self._do_trigger_handlers(f)

    def _do_trigger_handlers(self, restore_file: FSResource):
        global_describe = self.sf.describe()
        sobject_names = [x["name"] for x in global_describe["sobjects"]]

        if self.should_restore:
            with restore_file.open("r") as f:
                target_status = yaml.safe_load(f)
                self.options["handlers"] = list(target_status.keys())
        else:
            target_status = defaultdict(lambda: self.options["active"])

        namespace = self.options.get("namespace", "") + "__"
        if f"{namespace}Trigger_Handler__c" in sobject_names:
            pass
        elif "Trigger_Handler__c" in sobject_names:
            namespace = ""
        else:
            raise CumulusCIException(
                "Unable to locate the Trigger Handler sObject. "
                "Ensure the namespace option is set correctly."
            )

        proxy_obj = getattr(self.sf, f"{namespace}Trigger_Handler__c")
        trigger_handlers = self.sf.query(
            f"SELECT Id, {namespace}Class__c, {namespace}Object__c, {namespace}Active__c FROM {namespace}Trigger_Handler__c"
        )

        current_status = {}

        for handler in trigger_handlers.get("records", []):
            class_name = handler[f"{namespace}Class__c"]
            object_name = handler[f"{namespace}Object__c"]
            compound_name = f"{object_name}:{class_name}"

            if not self.options["handlers"] or any(
                [
                    class_name in self.options["handlers"],
                    object_name in self.options["handlers"],
                    compound_name in self.options["handlers"],
                ]
            ):
                current_status[compound_name] = handler[f"{namespace}Active__c"]
                proxy_obj.update(
                    handler["Id"],
                    {f"{namespace}Active__c": target_status[compound_name]},
                )

        if self.should_save:
            with restore_file.open("w") as f:
                yaml.safe_dump(current_status, f)
        elif self.should_restore:
            restore_file.unlink()

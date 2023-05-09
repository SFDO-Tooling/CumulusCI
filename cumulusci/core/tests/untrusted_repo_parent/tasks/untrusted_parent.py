from cumulusci.core.tasks import BaseTask


class UntrustedParentExampleTask(BaseTask):
    def _run_task(self):
        raise AssertionError("This should not be callable! (parent)")

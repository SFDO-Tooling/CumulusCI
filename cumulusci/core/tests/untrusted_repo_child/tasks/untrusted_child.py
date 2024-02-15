from cumulusci.core.tasks import BaseTask


class UntrustedChildExampleTask(BaseTask):
    def _run_task(self):
        raise AssertionError("This should not be callable (child)")

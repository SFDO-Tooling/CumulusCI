from cumulusci.core.tasks import BaseTask


class ExampleTask2(BaseTask):
    def _run_task(self):
        self.logger.info("Called _run_task 2.")

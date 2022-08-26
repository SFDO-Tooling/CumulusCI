from cumulusci.core.tasks import BaseTask


class ExampleTask(BaseTask):
    def _run_task(self):
        self.logger.info("Called _run_task 2 !!!!")

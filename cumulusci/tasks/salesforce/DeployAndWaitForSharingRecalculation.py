from datetime import datetime
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.salesforce.Deploy import Deploy
from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class SharingRecalculationTimeout(CumulusCIException):
    pass


class DeployAndWaitForSharingRecalculation(Deploy, BaseSalesforceApiTask):
    """
    Runs the Deploy task that starts a sharing recalculation then polls checking if sharing recalculation finishes before the timeout.  If the Deploy task does not start a sharing recalculation, this task will time out.
    When a sharing recalculation starts, a SetupAuditTrail record is inserted with Section 'Sharing Defaults' and Action 'owdUpdateStarted'.
    When a sharing recalculation finishes, a SetupAuditTrail record is inserted with Section 'Sharing Defaults' and Action 'owdUpdateFinished'.
    """

    task_options = {
        **Deploy.task_options,
        "timeout": {
            "description": "The max amount of time to wait in seconds.  Default: 600",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        """Defaults timeout as 600"""
        super(DeployAndWaitForSharingRecalculation, self)._init_options(kwargs)
        if not self.options.get("timeout"):
            self.options["timeout"] = "600"
        self.options["timeout"] = int(self.options["timeout"])

    def _get_last_setup_audit_trail_created_date(self):
        records = self.sf.query(
            "SELECT CreatedDate FROM SetupAuditTrail ORDER BY CreatedDate DESC LIMIT 1"
        ).get("records")
        return records[0].get("CreatedDate") if records else None

    def _log_title(self, title):
        """Logs title with an underline"""
        self.logger.info("")
        self.logger.info(title)
        self.logger.info("-" * len(title))

    def _run_task(self):
        """
        1) Set baselines to detect if:
           - the task times out
           - SetupAuditTrail records inserted due to our deployment
        2) Run the deploy which starts a sharing recalculation
        3) Poll checking if sharing recalculation completes
        """
        self.time_start = datetime.now()
        self.last_setup_audit_trail_created_date = (
            self._get_last_setup_audit_trail_created_date()
        )

        self._log_title("Deploying metadata")

        super(Deploy, self)._run_task()

        if self._is_sharing_recalcuation_started():
            self._log_title(
                f'Checking for {self.options["timeout"]} seconds if sharing recalculation is finished'
            )
            self._poll()
            self.logger.info("Sharing recalculation finished!".format(**self.options))
        else:
            self.log_title("Skipping check for sharing recalculation")
            self.logger.info(
                "A sharing recalculation wasn't started after deploying metadata."
            )

    def _get_sharing_recalculation_query(self):
        """
        When a sharing recalculation finishes, a SetupAuditTrail record is inserted with Section 'Sharing Defaults' and Action 'owdUpdateFinished'.

        If last_setup_audit_trail_created_date is None, then there were no SetupAuditTrail records before Deploy._run_task() was called.
        """
        if self.last_setup_audit_trail_created_date:
            return f"SELECT Action, Section FROM SetupAuditTrail WHERE CreatedDate > {self.last_setup_audit_trail_created_date} ORDER BY CreatedDate DESC"
        return f"SELECT Action, Section FROM SetupAuditTrail ORDER BY CreatedDate DESC"

    def _is_sharing_recalcuation_started(self):
        for record in self.sf.query(self._get_sharing_recalculation_query()).get(
            "records"
        ):
            if (
                record.get("Section") == "Sharing Defaults"
                and record.get("Action") == "owdUpdateStarted"
            ):
                return True
        return False

    def _is_sharing_recalcuation_finished(self):
        for record in self.sf.query(self._get_sharing_recalculation_query()).get(
            "records"
        ):
            if (
                record.get("Section") == "Sharing Defaults"
                and record.get("Action") == "owdUpdateFinished"
            ):
                return True
        return False

    def _poll_action(self):
        """
        When a sharing recalculation finishes, a SetupAuditTrail record is inserted with Section 'Sharing Defaults' and Action 'owdUpdateFinished'.

        To detect if sharing recalculation is finished, we:
        1) Find the latest SetupAuditTrail.CreatedDate before we deploy so we can
           detect all SetupAuditTrail records created after we deploy.
        2) Run the deploy which starts a sharing recalculation.
        3) Query only SetupAuditTrail records created after we deploy.
           Check if there is a record whose Section is 'Sharing Defaults' and
           Action is 'owdUpdateFinised' signifying sharing recalculation is finished.
        """
        elapsed = datetime.now() - self.time_start
        if elapsed.total_seconds() > self.options["timeout"]:
            raise SharingRecalculationTimeout(
                "Sharing recalculation did not finish after {timeout} seconds".format(
                    **self.options
                )
            )

        if self._is_sharing_recalcuation_finished():
            self.poll_complete = True

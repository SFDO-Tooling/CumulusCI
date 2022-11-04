from collections import defaultdict

from cumulusci.tasks.salesforce import BaseSalesforceApiTask


class CheckSObjectRecordTypes(BaseSalesforceApiTask):
    def _run_task(self):
        rts = defaultdict(list)
        records = self.tooling.query_all(
            "Select SobjectType, FullName FROM RecordType"
        )["records"]
        for r in records:
            rts[r["SobjectType"]].append(r["FullName"].split(".")[1])

        self.return_values = rts
        self.logger.info(f"Found existing Record Types: {self.return_values}")

from cumulusci.tasks.salesforce import BaseSalesforceApiTask
from collections import defaultdict


class CheckSObjectRecordTypes(BaseSalesforceApiTask):
    def _run_task(self):
        rts = defaultdict(list)
        records = self.tooling.query("Select SObjectType,FullName FROM RecordType")[
            "records"
        ]
        for r in records:
            rts[r["SobjectType"]].append(r["FullName"].split(".")[1])

        self.return_values = rts
        self.logger.info(f"Found existing recordtypes: {self.return_values}")

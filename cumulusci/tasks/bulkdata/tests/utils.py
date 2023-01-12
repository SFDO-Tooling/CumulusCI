from cumulusci.core.config import BaseProjectConfig, TaskConfig, UniversalConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.bulkdata.step import (
    BaseDmlOperation,
    DataOperationJobResult,
    DataOperationStatus,
)
from cumulusci.tests import util as cci_test_utils


def _make_task(task_class, task_config, org_config=None):
    task_config = TaskConfig(task_config)
    universal_config = UniversalConfig()
    project_config = BaseProjectConfig(
        universal_config,
        config={
            "noyaml": True,
            "project": {
                "package": {"api_version": cci_test_utils.CURRENT_SF_API_VERSION}
            },
        },
    )
    keychain = BaseProjectKeychain(project_config, "")
    project_config.set_keychain(keychain)
    org_config = org_config or cci_test_utils.DummyOrgConfig(
        {"instance_url": "https://example.com", "access_token": "abc123"}, "test"
    )
    return task_class(project_config, task_config, org_config)


class FakeBulkAPI:
    """Extremely simplistic mock of the bulk API

    Can be improved as needed over time.
    """

    next_job_id = 0
    next_batch_id = 0
    endpoint = f"https://example.my.salesforce.com/services/async/{cci_test_utils.CURRENT_SF_API_VERSION}"

    @classmethod
    def create_job(cls, *args, **kwargs):
        cls.next_job_id += 1
        return cls.next_job_id

    @classmethod
    def create_query_job(cls, *args, **kwargs):
        cls.next_job_id += 1
        return cls.next_job_id

    @classmethod
    def post_batch(cls, *args, **kwargs):
        cls.next_batch_id += 1
        return cls.next_batch_id

    def close_job(self, *args, **kwargs):
        pass

    def job_status(self, job_id):
        return {
            "numberBatchesCompleted": self.next_batch_id,
            "numberBatchesTotal": self.next_batch_id,
        }

    def query(self, job_id, soql):
        return self.post_batch()

    def get_query_batch_result_ids(self, batch_id, job_id):
        return range(0, 10)


class FakeBulkAPIDmlOperation(BaseDmlOperation):
    def __init__(
        self, *, context, sobject=None, operation=None, api_options=None, fields=None
    ):
        super().__init__(
            sobject=sobject,
            operation=operation,
            api_options=api_options,
            context=context,
            fields=fields,
        )
        self._results = []
        self.records = []

    def start(self):
        self.job_id = "JOB"

    def end(self):
        records_processed = len(self.results)
        self.job_result = DataOperationJobResult(
            DataOperationStatus.SUCCESS, [], records_processed, 0
        )

    def load_records(self, records):
        self.records.extend(records)

    def get_results(self):
        return iter(self.results)

    @property
    def results(self):
        return self._results

    @results.setter
    def results(self, results):
        self._results = results
        self.end()

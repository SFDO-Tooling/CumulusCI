from pathlib import Path

import pytest

from cumulusci.tasks.preflight.packages import GetInstalledPackages
from cumulusci.tasks.salesforce import SOQLQuery

pytestmark = pytest.mark.random_order(disabled=True)

first_cassette = (
    Path(__file__).parent
    / "cassettes/TestIntegrationInfrastructure.test_integration_tests.yaml"
)


@pytest.fixture()
def capture_orgid_using_task(create_task: callable, tmp_path: str) -> str:
    def _capture_orgid_using_task():
        csv_output = Path(tmp_path) / "foo.csv"
        t = create_task(
            SOQLQuery,
            {
                "query": "select Id from Organization",
                "object": "Organization",
                "result_file": csv_output,
            },
        )
        t()
        assert csv_output.exists()
        org_id = csv_output.read_text().split("\n")[1].split(",")[0]
        return org_id.strip('"')

    return _capture_orgid_using_task


class TestIntegrationInfrastructure:
    "Test our two plugins for doing integration testing"
    remembered_cli_specified_org_id = None

    @pytest.mark.vcr()
    def test_integration_tests(self, create_task, run_code_without_recording):
        # only delete the cassette if we can replace it
        def delete_cassette():
            if first_cassette.exists():
                first_cassette.unlink()

        run_code_without_recording(delete_cassette)
        task = create_task(GetInstalledPackages, {})
        assert task() is not None

    def test_file_was_created(self):

        assert first_cassette.exists(), first_cassette
        with first_cassette.open() as f:
            data = f.read()
            assert "Bearer 0" not in data
            assert "Public-Key-Pins-Report-Only" not in data
            assert "<sessionId>00" not in data

    @pytest.mark.vcr()
    def test_run_code_without_recording(
        self, run_code_without_recording, sf, create_task
    ):
        def setup():
            task = create_task(
                SOQLQuery,
                {
                    "query": "select Id from Organization",
                    "object": "Organization",
                    "result_file": "foo.csv",
                },
            )
            task()

        run_code_without_recording(lambda: setup())

    def test_file_was_not_created(self, capture_orgid_using_task):
        filename = (
            Path(__file__).parent
            / "cassettes/TestIntegrationInfrastructure.test_run_code_without_recording.yaml"
        )

        assert not filename.exists(), filename

    @pytest.mark.needs_org()
    def test_cli_specified_org(self, capture_orgid_using_task):
        self.__class__.remembered_cli_specified_org_id = capture_orgid_using_task()
        assert self.remembered_cli_specified_org_id.startswith(
            "00D"
        ), self.__class__.remembered_cli_specified_org_id

    @pytest.mark.needs_org()
    @pytest.mark.slow()
    @pytest.mark.org_shape("qa", "qa_org")
    def test_org_shape(self, capture_orgid_using_task, current_org_shape):
        assert (
            current_org_shape.org_config.sfdx_alias == "CumulusCI__pytest__qa__qa_org"
        )
        assert self.__class__.remembered_cli_specified_org_id
        generated_org_id = capture_orgid_using_task()
        assert self.__class__.remembered_cli_specified_org_id != generated_org_id, (
            self.__class__.remembered_cli_specified_org_id,
            generated_org_id,
        )
        self.__class__.remember_generated_org_id = generated_org_id

    @pytest.mark.needs_org()
    @pytest.mark.slow()
    @pytest.mark.org_shape("qa", "qa_org")
    def test_org_shape_reuse(
        self,
        create_task,
        current_org_shape,
        tmp_path,
        capture_orgid_using_task,
    ):
        assert (
            current_org_shape.org_config.sfdx_alias == "CumulusCI__pytest__qa__qa_org"
        )
        generated_org_id = capture_orgid_using_task()
        assert generated_org_id == self.__class__.remember_generated_org_id

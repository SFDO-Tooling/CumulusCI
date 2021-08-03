import pytest
from cumulusci.tasks.preflight.packages import GetInstalledPackages
from pathlib import Path

from cumulusci.tasks.salesforce import SOQLQuery

pytestmark = pytest.mark.random_order(disabled=True)

first_cassette = (
    Path(__file__).parent
    / "cassettes/TestIntegrationInfrastructure.test_integration_tests.yaml"
)


class TestIntegrationInfrastructure:
    "Test our two plugins for doing integration testing"

    @pytest.mark.vcr()
    def test_integration_tests(self, create_task, run_code_without_recording):
        # only delete the cassette if we can replace it
        def delete_cassette():
            if first_cassette.exists():
                first_cassette.unlink(missing_ok=True)

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

    def test_file_was_not_created(self):
        filename = (
            Path(__file__).parent
            / "cassettes/TestIntegrationInfrastructure.test_run_code_without_recording.yaml"
        )

        assert not filename.exists(), filename

    @pytest.mark.needs_org()
    @pytest.mark.slow()
    def test_org_shape(self, org_shape, create_task, current_org_shape, tmp_path):
        with org_shape("qa", "qa_org"):
            csv_output = Path(tmp_path) / "foo.csv"
            assert (
                current_org_shape.org_config.sfdx_alias
                == "CumulusCI__pytest__qa__qa_org"
            )
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

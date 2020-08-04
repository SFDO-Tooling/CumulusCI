import pytest
from cumulusci.tasks.preflight.packages import GetInstalledPackages
from pathlib import Path


class TestIntegrationInfrastructure:
    "Test our two plugins for doing integration testing"

    @pytest.mark.vcr()
    def test_integration_tests(self, create_task):
        task = create_task(GetInstalledPackages, {})
        assert task() is not None

    def test_file_was_created(self):
        filename = (
            Path(__file__).parent
            / "cassettes/TestIntegrationInfrastructure.test_integration_tests.yaml"
        )

        assert filename.exists(), filename
        with filename.open() as f:
            data = f.read()
            assert "Bearer 0" not in data
            assert "Public-Key-Pins-Report-Only" not in data
            assert "<sessionId>00" not in data

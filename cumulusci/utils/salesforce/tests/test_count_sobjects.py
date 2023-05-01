import pytest
import vcr

from cumulusci.utils.salesforce.count_sobjects import count_sobjects


class TestCountSObjects:
    @pytest.mark.vcr()
    def test_count_sobjects_simple(self, sf):
        results, net_errors, sf_errors = count_sobjects(sf, ["Account", "Opportunity"])
        assert "Account" in results
        assert "Opportunity" in results
        assert not net_errors and not sf_errors

    @pytest.mark.vcr()
    def test_count_sobjects__errors(self, sf):
        results, net_errors, sf_errors = count_sobjects(sf, ["Account", "XYZZY"])
        assert "Account" in results
        assert "XYZZY" not in results
        assert not net_errors
        assert sf_errors and "XYZZY" in str(sf_errors)

    @pytest.mark.vcr()
    def test_count_sobjects__network_errors(self, sf):
        network_errors_yaml = "cumulusci/utils/salesforce/tests/cassettes/ManualEdit_TestCountSObjects.test_count_sobjects__network_errors.yaml"
        with vcr.use_cassette(network_errors_yaml):
            _, net_errors, sf_errors = count_sobjects(sf, ["Account", "XYZZY"])
            assert net_errors
            assert not sf_errors

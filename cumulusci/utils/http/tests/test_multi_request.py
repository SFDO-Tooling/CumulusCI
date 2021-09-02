import pytest

from cumulusci.utils.http.multi_request import CompositeParallelSalesforce


class TestCompositeParallelSalesforce:
    @pytest.mark.vcr()
    def test_composite_parallel_salesforce(
        self, sf, run_code_without_recording, delete_data_from_org
    ):
        run_code_without_recording(lambda: delete_data_from_org("Entitlement,Account"))
        sf.Account.create(
            {"Name": "Smith Corp."},
        )
        requests = [
            {
                "method": "GET",
                "url": "/services/data/v50.0/query?q=SELECT Id FROM Account LIMIT 1",
            },
            {
                "method": "GET",
                "url": "/services/data/v50.0/query?q=SELECT Name FROM Account LIMIT 1",
            },
        ] * 2
        with CompositeParallelSalesforce(sf, 5, max_workers=1) as cpsf:
            results = cpsf.do_composite_requests(requests)
        assert len(list(results)) == len(requests)
        for result in results:
            assert result["body"]
            assert result["body"]["done"]
            assert result["body"]["records"][0]["attributes"]

    @pytest.mark.vcr()
    def test_not_opened(self, sf):
        cpsf = CompositeParallelSalesforce(sf, 5, max_workers=1)
        with pytest.raises(AssertionError):
            cpsf.do_composite_requests([])

    @pytest.mark.vcr()
    def test_empty(self, sf):
        with CompositeParallelSalesforce(sf, 5, max_workers=1) as cpsf:
            results = cpsf.do_composite_requests([])
            assert list(results) == []

    @pytest.mark.vcr()
    def test_http_headers(self, sf, vcr):
        requests = [
            {
                "method": "GET",
                "url": "/services/data/v50.0/sobjects",
                "httpHeaders": {"If-Modified-Since": "Thu, 03 Sep 2020 21:35:07 GMT"},
            },
        ] * 3
        # don't re-record this one because you'll need to fiddle
        # with the dates
        with vcr.use_cassette(
            "ManualEditTestCompositeParallelSalesforce.test_http_headers.yaml"
        ):
            with CompositeParallelSalesforce(sf, 4, max_workers=1) as cpsf:
                results = cpsf.do_composite_requests(requests)
        assert results[0]["httpStatusCode"] == 304

    @pytest.mark.vcr()
    def test_reference_ids(self, sf, run_code_without_recording, delete_data_from_org):
        run_code_without_recording(lambda: delete_data_from_org("Account"))
        requests = [
            {
                "method": "GET",
                "url": "/services/data/v50.0/query?q=SELECT Id FROM Account LIMIT 1",
                "referenceId": "one",
            },
            {
                "method": "GET",
                "url": "/services/data/v50.0/query?q=SELECT Name FROM Account LIMIT 1",
                "referenceId": "two",
            },
            {
                "method": "GET",
                "url": "/services/data/v50.0/query?q=SELECT Name FROM Account LIMIT 1",
                "referenceId": "three",
            },
        ]
        with CompositeParallelSalesforce(sf, 2, max_workers=1) as cpsf:
            results = cpsf.do_composite_requests(requests)
        assert len(list(results)) == len(requests)
        assert set(result["referenceId"] for result in results) == set(
            request["referenceId"] for request in requests
        )

    @pytest.mark.vcr()
    def test_errors(self, sf):
        requests = [{"method": "GET", "url": "/services/data/v50.0/sobjects/Foo"}]
        with CompositeParallelSalesforce(sf, 4, max_workers=1) as cpsf:
            results = cpsf.do_composite_requests(requests)
        assert results[0]["httpStatusCode"] == 404, results[0]["httpStatusCode"]

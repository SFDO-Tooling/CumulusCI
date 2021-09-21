import pytest
import responses

from cumulusci.tests.util import FakeUnreliableRequestHandler
from cumulusci.utils.http.multi_request import CompositeParallelSalesforce

COMPOSITE_RESPONSE = {
    "compositeResponse": [
        {
            "body": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "Account",
                            "url": "/services/data/v49.0/sobjects/Account/0013B00000ddh3PQAQ",
                        },
                        "Id": "0013B00000ddh3PQAQ",
                    }
                ],
            },
            "httpHeaders": {},
            "httpStatusCode": 200,
            "referenceId": "one",
        },
        {
            "body": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "Account",
                            "url": "/services/data/v49.0/sobjects/Account/0013B00000ddh7qQAA",
                        },
                        "Name": "Elizabeth Foster",
                    }
                ],
            },
            "httpHeaders": {},
            "httpStatusCode": 200,
            "referenceId": "two",
        },
    ]
}


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
            results, errors = cpsf.do_composite_requests(requests)

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
            results, errors = cpsf.do_composite_requests([])
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
                results, errors = cpsf.do_composite_requests(requests)
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
            results, errors = cpsf.do_composite_requests(requests)
        assert len(list(results)) == len(requests)
        assert set(result["referenceId"] for result in results) == set(
            request["referenceId"] for request in requests
        )

    @pytest.mark.vcr()
    def test_errors(self, sf):
        requests = [{"method": "GET", "url": "/services/data/v50.0/sobjects/Foo"}]
        with CompositeParallelSalesforce(sf, 4, max_workers=1) as cpsf:
            results, errors = cpsf.do_composite_requests(requests)
        assert results[0]["httpStatusCode"] == 404, results[0]["httpStatusCode"]

    @responses.activate
    def test_multirequest_timeout(self, sf):
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
        ] * 2

        composite_handler = FakeUnreliableRequestHandler(COMPOSITE_RESPONSE)
        responses.add_callback(
            responses.POST,
            f"{sf.base_url}composite",
            callback=composite_handler.request_callback,
            content_type="application/json",
        )

        single_request_handler = FakeUnreliableRequestHandler(COMPOSITE_RESPONSE)
        responses.add_callback(
            responses.GET,
            f"{sf.base_url}query?q=SELECT%20Id%20FROM%20Account%20LIMIT%201",
            callback=single_request_handler.request_callback,
            content_type="application/json",
        )

        with CompositeParallelSalesforce(sf, 2, max_workers=1) as cpsf:
            results, errors = cpsf.do_composite_requests(requests)
        assert len(errors) == 1  # one of the single requests fails after retry
        assert len(results) == 5  # 4 succeed first time, one fails on retry

        assert single_request_handler.counter == 2
        assert composite_handler.counter == 3

    @responses.activate
    def test_multirequest_unknown_exception(self, sf):
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
        ] * 2

        with CompositeParallelSalesforce(sf, 2, max_workers=1) as cpsf:
            results, errors = cpsf.do_composite_requests(requests)
        assert len(errors) == 3  # all should be rejected by Responses.
        assert len(results) == 0

    @responses.activate
    def test_multirequest_timeout_POSTs(self, sf):
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
                "method": "POST",
                "url": "/services/data/v50.0/query?q=SELECT Name FROM Account LIMIT 1",
                "referenceId": "three",
            },
        ] * 2

        composite_handler = FakeUnreliableRequestHandler(COMPOSITE_RESPONSE)
        responses.add_callback(
            responses.POST,
            f"{sf.base_url}composite",
            callback=composite_handler.request_callback,
            content_type="application/json",
        )

        single_request_handler = FakeUnreliableRequestHandler(COMPOSITE_RESPONSE)
        responses.add_callback(
            responses.GET,
            f"{sf.base_url}query?q=SELECT%20Id%20FROM%20Account%20LIMIT%201",
            callback=single_request_handler.request_callback,
            content_type="application/json",
        )

        with CompositeParallelSalesforce(sf, 2, max_workers=1) as cpsf:
            results, errors = cpsf.do_composite_requests(requests)

        # Three chunks of 2. SUCCEED, FAIL, SUCCEED
        assert composite_handler.counter == 3

        # The GET in the failing chunk should be retried and succeed
        # The POST should not.
        assert len(errors) == 1, str(errors)
        assert single_request_handler.counter == 1

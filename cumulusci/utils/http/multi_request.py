import typing as T
from concurrent.futures import as_completed
from itertools import chain

from requests.exceptions import ReadTimeout
from requests_futures.sessions import FuturesSession

from cumulusci.utils.iterators import iterate_in_chunks, partition

RECOVERABLE_ERRORS = (ReadTimeout, ConnectionError)


class HTTPRequestError(T.NamedTuple):
    exception: Exception
    request: dict


class ParallelHTTP:
    """A parallelized HTTP client as a context manager"""

    def __init__(self, base_url, max_workers=32):
        self.base_url = base_url
        self.max_workers = max_workers

    def __enter__(self, *args):
        self.session = FuturesSession(max_workers=self.max_workers)
        return self

    def __exit__(self, *args):
        self.session.close()

    def _async_request(
        self, url: str, method: str, json: object = None, httpHeaders: dict = None
    ):
        "Make an async HTTP request and return a future"
        headers = {**(httpHeaders or {}), "Accept-Encoding": "gzip"}
        return self.session.request(
            method=method,
            url=self.base_url + url.lstrip("/"),
            headers=headers,
            json=json,
            timeout=30,
        )

    def do_requests(self, requests: T.Iterable[T.Dict]):
        """Initiate requests and wait for them to complete.

        Returns a tuple with a sequence of successes and a sequence of failures.
        """

        futures_to_requests = {
            self._async_request(**request): request for request in requests
        }

        results = (
            future_with_exception_handling(future, futures_to_requests)
            for future in as_completed(futures_to_requests.keys())
        )
        successes, errors = collate_results(results)

        return successes, errors


def future_with_exception_handling(future, futures_to_requests):
    try:
        return future.result()
    except Exception as e:
        return HTTPRequestError(exception=e, request=futures_to_requests[future])


def collate_results(result_iterable: T.Sequence) -> T.Tuple[T.Generator, T.Generator]:
    """Partition results into separate sequences of successes and errors."""
    return partition(lambda r: isinstance(r, HTTPRequestError), result_iterable)


class ParallelSalesforce(ParallelHTTP):
    """A context-managed HTTP client that can parallelize access to a Simple-Salesforce connection"""

    def __init__(self, sf, max_workers=32):
        self.sf = sf
        base_url = self.sf.base_url.rstrip("/") + "/"
        super().__init__(base_url, max_workers)

    def _async_request(
        self, url: str, method: str, json: object = None, httpHeaders: dict = None
    ):
        headers = {**self.sf.headers, **(httpHeaders or {})}
        return super()._async_request(url, method, json, headers)


def create_composite_requests(requests, chunk_size):
    """Format Composite Salesforce messages"""

    def ensure_request_id(idx, request):
        # generate a new request dicts with a defaulted request_id
        return {"referenceId": f"CCI__RefId__{idx}__", **request}

    requests = [ensure_request_id(idx, request) for idx, request in enumerate(requests)]

    return (
        {"url": "composite", "method": "POST", "json": {"compositeRequest": chunk}}
        for chunk in iterate_in_chunks(chunk_size, requests)
    )


def parse_composite_results(composite_results):
    individual_results = chain.from_iterable(
        result.json()["compositeResponse"] for result in composite_results
    )

    return individual_results


IDEMPOTENT_METHODS = ("GET", "PUT")


class CompositeParallelSalesforce:
    """Salesforce Session which uses the Composite API multiple times
    in parallel.
    """

    max_workers = 32
    chunk_size = 25  # max composite batch size
    psf = None

    def __init__(self, sf, chunk_size=None, max_workers=None):
        self.sf = sf
        self.chunk_size = chunk_size or self.chunk_size
        self.max_workers = max_workers or self.max_workers

    def open(self):
        self.psf = ParallelSalesforce(self.sf, self.max_workers)
        self.psf.__enter__()

    def close(self):
        self.psf.__exit__()

    def __enter__(self, *args):
        self.open()
        return self

    def __exit__(self, *args):
        self.close()

    def do_composite_requests(
        self, requests
    ) -> T.Tuple[T.Sequence, T.Sequence]:  # results, errors
        if not self.psf:
            raise AssertionError(
                "Session was not opened. Please call open() or use as a context manager"
            )

        composite_requests = create_composite_requests(requests, self.chunk_size)
        composite_results, errors = self.psf.do_requests(composite_requests)
        individual_results = parse_composite_results(composite_results)

        errors = list(errors)
        if errors:
            singleton_results, unrecoverable_errors = self.retry_errors(errors)
        else:
            singleton_results = []
            unrecoverable_errors = []

        individual_results = list(individual_results)

        individual_results += list(singleton_results)
        return individual_results, unrecoverable_errors

    def retry_errors(self, errors: T.List[HTTPRequestError]):
        "Retry all composite requests that had errors."
        unrecoverable_errors = []
        singleton_requests = []
        for error in errors:
            if isinstance(error.exception, RECOVERABLE_ERRORS):
                single_requests = split_requests(error.request)
                for request in single_requests:
                    if request["method"] in IDEMPOTENT_METHODS:
                        singleton_requests.append(request)
                    else:
                        unrecoverable_errors.append(
                            HTTPRequestError(error.exception, request)
                        )
            else:
                unrecoverable_errors.append(error)

        singleton_results, errors = self.psf.do_requests(singleton_requests)

        def response_to_dict(response):
            return {
                "httpStatusCode": response.status_code,
                "body": response.json(),
                "httpHeaders": response.headers,
            }

        singleton_results = [
            response_to_dict(response) for response in singleton_results
        ]
        errors = list(errors)

        return singleton_results, unrecoverable_errors + errors


def split_requests(composite_request: dict):
    # need to remove this prefix-pattern because it will be added again later
    prefix = "/services/data/"
    single_requests = [r.copy() for r in composite_request["json"]["compositeRequest"]]
    for request in single_requests:
        del request["referenceId"]
        if request["url"].startswith(prefix):
            url_with_version = request["url"][len(prefix) :]
            assert url_with_version.startswith("v"), url_with_version
            url_without_version = url_with_version.split("/", 1)[1]
            request["url"] = f"/{url_without_version}"
    return single_requests

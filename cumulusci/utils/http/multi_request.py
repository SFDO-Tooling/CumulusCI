from itertools import chain
from concurrent.futures import as_completed

from requests_futures.sessions import FuturesSession


class ParallelSalesforce:
    def __init__(self, sf, max_workers=32):
        self.sf = sf
        self.max_workers = max_workers
        self.base_url = self.sf.base_url.rstrip("/") + "/"

    def __enter__(self, *args):
        self.session = FuturesSession(max_workers=self.max_workers)
        return self

    def __exit__(self, *args):
        self.session.close()

    def async_request(self, path, method, json=None, headers={}):

        headers = {**self.sf.headers, **headers, "Accept-Encoding": "gzip"}
        return self.session.request(
            method=method,
            url=self.base_url + path.lstrip("/"),
            headers=headers,
            # data=dumps(json),
            json=json,
        )


class CompositeParallelSalesforce:
    max_workers = 32
    chunk_size = 25  # max composite batch size

    def __init__(self, sf, chunk_size=25, max_workers=32):
        self.sf = sf
        self.chunk_size = chunk_size
        self.max_workers = max_workers

    def __enter__(self, *args):
        self.psf = ParallelSalesforce(self.sf, self.max_workers)
        self.psf.__enter__(*args)
        return self

    def __exit__(self, *args):
        self.psf.__exit__(*args)

    def _do_composite_request(self, requests: list):
        request = {
            "compositeRequest": requests,
        }

        return self.psf.async_request(path="composite", method="POST", json=request,)

    def composite_requests(self, requests):
        futures = [
            self._do_composite_request(chunk)
            for chunk in chunks(list(requests), self.chunk_size)
        ]

        def validate(x):
            if isinstance(x, list):
                assert "errorCode" not in x[0], x
            return x

        composite_results = (future.result() for future in as_completed(futures))

        individual_results = chain.from_iterable(
            validate(result.json())["compositeResponse"] for result in composite_results
        )

        return individual_results


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]

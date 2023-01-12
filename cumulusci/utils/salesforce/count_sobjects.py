import typing as T

from simple_salesforce import Salesforce

from cumulusci.utils.http.multi_request import CompositeParallelSalesforce
from cumulusci.utils.iterators import partition


class ObjectCount(T.NamedTuple):
    counts: T.Dict[str, int]
    transport_errors: T.Sequence[dict]  # e.g. couldn't reach server
    salesforce_errors: T.Sequence[dict]  # e.g. 404, 401


def count_sobjects(sf: Salesforce, objs: T.Sequence[str]) -> ObjectCount:
    """Quickly count SObjects using SOQL and Parallelization"""
    with CompositeParallelSalesforce(sf, max_workers=8, chunk_size=5) as cpsf:
        responses, transport_errors = cpsf.do_composite_requests(
            (
                {
                    "method": "GET",
                    "url": f"/services/data/v{sf.sf_version}/query/?q=select count() from {obj}",
                    "referenceId": f"ref{obj}",
                }
                for obj in objs
            )
        )
        salesforce_errors, successes = partition(
            lambda response: response["httpStatusCode"] == 200, responses
        )

        transport_errors = tuple(error._asdict() for error in transport_errors)

    successes = list(successes)

    def removeprefix(mainstr: str, prefix: str):
        # Until Python 3.9 is minimum supported
        a, b = mainstr[0 : len(prefix)], mainstr[len(prefix) :]
        assert a == prefix
        return b

    ret = {
        removeprefix(response["referenceId"], "ref"): response["body"]["totalSize"]
        for response in successes
    }
    return ObjectCount(ret, transport_errors, tuple(salesforce_errors))

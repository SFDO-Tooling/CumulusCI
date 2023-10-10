from concurrent.futures import Future, ThreadPoolExecutor
from unittest.mock import MagicMock, patch

import pytest

from cumulusci.utils.parallel.queries_in_parallel.run_queries_in_parallel import (
    RunParallelQueries,
)


def run_query(query):
    return {"test": query}


def test_run_queries_in_parallel():
    queries = {
        "query1": "SELECT * FROM Table1",
        "query2": "SELECT * FROM Table2",
    }

    expected_results = {
        "query1": [{"field1": "value1"}, {"field1": "value2"}],
        "query2": [{"field2": "value3"}, {"field2": "value4"}],
    }

    mock_future1 = MagicMock()
    mock_future1.result.return_value = {"records": expected_results["query1"]}
    mock_future2 = MagicMock()
    mock_future2.result.return_value = {"records": expected_results["query2"]}

    with patch.object(ThreadPoolExecutor, "submit") as mock_submit:
        mock_submit.side_effect = [mock_future1, mock_future2]

        results_dict = RunParallelQueries._run_queries_in_parallel(queries, run_query)

    assert results_dict == expected_results


def test_run_queries_in_parallel_with_exception():
    queries = {
        "Query1": "SELECT Id FROM Table1",
    }

    with patch.object(Future, "result", side_effect=Exception("Test exception")):
        with pytest.raises(Exception) as excinfo:
            RunParallelQueries._run_queries_in_parallel(queries, run_query=run_query)
        assert (
            "Error executing query 'Query1': <class 'Exception'>: Test exception"
            == str(excinfo.value)
        )

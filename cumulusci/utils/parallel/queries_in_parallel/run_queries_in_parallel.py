from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Dict


class RunParallelQueries:
    @staticmethod
    def _run_queries_in_parallel(
        queries: Dict[str, str], run_query: Callable[[str], dict], num_threads: int = 4
    ) -> Dict[str, list]:
        """Accepts a set of queries structured as {'query_name': 'query'}
        and a run_query function that runs a particular query. Runs queries in parallel and returns the queries"""
        results_dict = {}

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = {
                query_name: executor.submit(run_query, query)
                for query_name, query in queries.items()
            }

        for query_name, future in futures.items():
            try:
                query_result = future.result()
                results_dict[query_name] = query_result["records"]
            except Exception as e:
                raise Exception(f"Error executing query '{query_name}': {type(e)}: {e}")
            else:
                queries.pop(query_name, None)

        return results_dict

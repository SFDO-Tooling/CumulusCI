import functools


class SOQLQueryCache:
    def __init__(self):
        @functools.lru_cache(1024)
        def _cached_query(instance, query):
            assert self.sf.sf_instance == instance
            return self.sf.query_all(query)

        self._cached_query = _cached_query

    def query_all(self, sf, query):
        org = sf.sf_instance
        print((org, query))
        self.sf = sf
        try:
            return self._cached_query(org, query)
        finally:
            del self.sf

    def return_query_records(self, sf, query):
        res = self.query_all(sf, query)
        if res["totalSize"] > 0:
            return res["records"]
        else:
            return []

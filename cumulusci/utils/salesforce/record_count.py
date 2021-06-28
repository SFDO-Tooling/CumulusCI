import time
import threading
import typing as T
from simple_salesforce import Salesforce


class OrgRecordCounts(threading.Thread):
    """A thread that asynchronously updates a local cache of org record counts"""

    main_sobject_count = None
    other_inaccurate_record_counts = {}
    daemon = True  # this is a background thread. Don't block exit.

    def __init__(
        self,
        sf: Salesforce,
        main_sobject: T.Optional[str] = None,
        update_frequency: int = 17,
    ):
        self.main_sobject = main_sobject
        self.sf = sf
        self.update_frequency = update_frequency
        super().__init__(daemon=True)

    def run(self):
        while 1:
            if self.main_sobject:
                self.main_sobject_count = get_record_count_for_sobject(
                    self.sf, self.main_sobject
                )
            self.other_inaccurate_record_counts = get_record_counts(self.sf)
            time.sleep(self.update_frequency)


def get_record_count_for_sobject(sf: Salesforce, sobject: str) -> T.Optional[int]:
    """Use SOQL or other fallback to look up record count

    This lags quite a bit behind the real numbers in large orgs.

    If SOQL fails, we fall back to the record_counts API which is somewhat innaccurate.
    """
    try:
        query = f"select count(Id) from {sobject}"
        count = sf.query(query)["records"][0]["expr0"]
        return int(count)
    except Exception:
        all_counts = get_record_counts(sf)
        return all_counts[sobject]


BLOCKWORDS = ["Permission", "History", "ListView", "Feed", "Setup", "Event"]


def get_record_counts(sf: Salesforce):
    "Return record counts for"
    data = sf.restful("limits/recordCount")

    rc = {
        sobject["name"]: sobject["count"]
        for sobject in data["sObjects"]
        if not any(blockword in sobject["name"] for blockword in BLOCKWORDS)
    }
    total = sum(rc.values())
    rc["TOTAL"] = total
    return rc

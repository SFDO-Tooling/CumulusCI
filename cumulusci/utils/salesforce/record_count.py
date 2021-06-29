import time
import threading
import typing as T
from simple_salesforce import Salesforce, SalesforceError
from logging import getLogger, Logger


class OrgRecordCounts(threading.Thread):
    """A thread that asynchronously updates a local cache of org record counts"""

    main_sobject_count = None
    other_inaccurate_record_counts = {}
    daemon = True  # this is a background thread. Don't block exit.

    def __init__(
        self,
        sf: Salesforce,
        relevant_sobjects: T.Sequence[str] = (),
        main_sobject: T.Optional[str] = None,
        update_frequency: int = 17,
    ):
        self.main_sobject = main_sobject
        ## TODO: Refresh auth token periodically, probably on exception.
        self.sf = sf
        self.update_frequency = update_frequency
        self.logger = getLogger(__file__)
        self.relevant_sobjects = relevant_sobjects
        if main_sobject:
            assert (
                main_sobject in relevant_sobjects
            ), f"{main_sobject} not in {relevant_sobjects}"
        super().__init__(daemon=True)

    def run(self):
        # TODO: Consider exception handling so this loop doesn't die
        # in case of intermittent errors
        while 1:
            try:
                if self.main_sobject:
                    self.main_sobject_count = get_record_count_for_sobject(
                        self.sf, self.main_sobject, self.logger
                    )
                self.other_inaccurate_record_counts = get_record_counts(
                    self.sf, self.relevant_sobjects
                )
            except Exception as e:
                self.logger.warn(e)
            time.sleep(self.update_frequency)


def get_record_count_for_sobject(sf: Salesforce, sobject: str, logger: Logger) -> int:
    """Use SOQL or other fallback to look up record count

    This lags quite a bit behind the real numbers in large orgs.

    If SOQL fails, we fall back to the record_counts API which is somewhat innaccurate.
    """
    try:
        query = f"select count(Id) from {sobject}"
        res = sf.query(query)
        record = res["records"][0]
        count = record["expr0"]
        return int(count)
    except (SalesforceError, OSError) as e:  # Todo tighten this up.
        logger.warn(f"Error getting record counts {e}")
        all_counts = get_record_counts(sf, (sobject,))
        return all_counts[sobject]


# BLOCKWORDS = ["Permission", "History", "ListView", "Feed", "Setup", "Event"]


def get_record_counts(sf: Salesforce, relevant_sobjects: T.Sequence[str]):
    "Return record counts for"
    data = sf.restful("limits/recordCount")

    rc = {
        sobject["name"]: sobject["count"]
        for sobject in data["sObjects"]
        if sobject["name"] in relevant_sobjects
    }
    total = sum(rc.values())
    rc["TOTAL"] = total
    return rc

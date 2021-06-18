import time
import threading
import typing as T


class OrgRecordCounts(threading.Thread):
    # Getting record count can be slow in big orgs
    main_sobject_count = 0
    other_inaccurate_record_counts = {}

    def __init__(self, main_sobject: str, sf):
        self.main_sobject = main_sobject
        self.sf = sf
        super().__init__(daemon=True)

    # TODO: WHAT if main_sobject_count can't be retrieved?
    #       Should get it from other_inaccurate_record_counts
    #       If both fail we'll have a problem. :(
    def run(self):
        while 1:
            self.main_sobject_count = self.get_org_record_count_for_sobject()
            self.other_inaccurate_record_counts = self.get_org_record_counts()
            time.sleep(17)

    def get_org_record_count_for_sobject(self) -> T.Optional[int]:
        "This lags quite a bit behind the real numbers."
        sobject = self.main_sobject
        if sobject:
            query = f"select count(Id) from {sobject}"
            count = self.sf.query(query)["records"][0]["expr0"]
            return int(count)

    def get_org_record_counts(self):
        data = self.sf.restful("limits/recordCount")
        blockwords = ["Permission", "History", "ListView", "Feed", "Setup", "Event"]
        rc = {
            sobject["name"]: sobject["count"]
            for sobject in data["sObjects"]
            if sobject["count"] > 100
            and not any(blockword in sobject["name"] for blockword in blockwords)
        }
        total = sum(rc.values())
        rc["TOTAL"] = total
        return rc

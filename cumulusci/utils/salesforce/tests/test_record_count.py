from unittest import mock
from logging import getLogger

from simple_salesforce.exceptions import SalesforceMalformedRequest

import pytest

from cumulusci.utils.salesforce.record_count import (
    OrgRecordCounts,
    get_record_count_for_sobject,
    get_record_counts,
)


LOGGER = getLogger(__name__)


class TestOrgRecordCounts:
    @pytest.mark.vcr()
    def test_get_record_count_for_sobject(self, sf):
        with mock.patch(
            "cumulusci.utils.salesforce.record_count.get_record_counts",
            wraps=get_record_counts,
        ) as wrapped_get_record_counts:
            assert get_record_count_for_sobject(sf, "Account", LOGGER) > 0
        assert len(wrapped_get_record_counts.mock_calls) == 0

    @pytest.mark.vcr()
    def test_get_record_counts(self, sf):
        assert (
            get_record_counts(sf, ("Account", "Contact", "Opportunity")).get("Contact")
            > 0
        )

    @pytest.mark.vcr()
    def test_get_record_counts__query_fails(self, sf):
        with mock.patch.object(
            sf, "query", side_effect=SalesforceMalformedRequest("", None, None, None)
        ), mock.patch(
            "cumulusci.utils.salesforce.record_count.get_record_counts",
            wraps=get_record_counts,
        ) as wrapped_get_record_counts:

            # falls back
            assert get_record_count_for_sobject(sf, "Contact", LOGGER)
            assert len(wrapped_get_record_counts.mock_calls) == 1

    @pytest.mark.vcr()
    def test_count_loop(self, sf):
        orc = OrgRecordCounts(sf, ("Opportunity", "Account"), "Opportunity")

        class MySleeper:
            count = 0

            def sleep(self, _):
                "Pretend-sleep once then throw an exception"
                self.count += 1
                if self.count >= 2:
                    raise StopIteration()

        with mock.patch("time.sleep", MySleeper().sleep):
            try:
                orc.run()
            except StopIteration:
                pass
        assert orc.main_sobject_count
        assert orc.other_inaccurate_record_counts["Account"]

from datetime import date, datetime, timedelta

from cumulusci.tasks.bulkdata.dates import (
    adjust_relative_dates,
    datetime_from_salesforce,
    salesforce_from_datetime,
)
from cumulusci.tasks.bulkdata.mapping_parser import MappingStep
from cumulusci.tasks.bulkdata.step import DataOperationType


class TestRelativeDates:
    def test_relative_dates(self):
        mapping = MappingStep(
            sf_object="Account", fields=["Some_Date__c"], anchor_date="2020-07-01"
        )

        target = date.today() + timedelta(days=7)
        assert adjust_relative_dates(
            mapping, ([0], [], date.today()), ["2020-07-08"], DataOperationType.INSERT
        ) == [target.isoformat()]

        assert adjust_relative_dates(
            mapping, ([0], [], date.today()), ["2020-07-01"], DataOperationType.INSERT
        ) == [date.today().isoformat()]

        assert adjust_relative_dates(
            mapping, ([0], [], date.today()), [""], DataOperationType.INSERT
        ) == [""]

    def test_relative_dates__extract(self):
        mapping = MappingStep(
            sf_object="Account", fields=["Some_Date__c"], anchor_date="2020-07-01"
        )

        target = mapping.anchor_date + timedelta(days=7)
        input_date = (date.today() + timedelta(days=7)).isoformat()
        assert (
            adjust_relative_dates(
                mapping,
                ([1], [], date.today()),
                ["001000000000000", input_date],
                DataOperationType.QUERY,
            )
            == ["001000000000000", target.isoformat()]
        )

        assert (
            adjust_relative_dates(
                mapping,
                ([1], [], date.today()),
                ["001000000000000", date.today().isoformat()],
                DataOperationType.QUERY,
            )
            == ["001000000000000", mapping.anchor_date.isoformat()]
        )

        assert (
            adjust_relative_dates(
                mapping,
                ([1], [], date.today()),
                ["001000000000000", ""],
                DataOperationType.QUERY,
            )
            == ["001000000000000", ""]
        )

    def test_relative_datetimes(self):
        mapping = MappingStep(
            sf_object="Account", fields=["Some_Datetime__c"], anchor_date="2020-07-01"
        )

        input_dt = datetime_from_salesforce("2020-07-08T09:37:57.373+0000")
        target = datetime.combine(date.today() + timedelta(days=7), input_dt.time())
        assert (
            adjust_relative_dates(
                mapping,
                ([], [0], date.today()),
                [salesforce_from_datetime(input_dt)],
                DataOperationType.INSERT,
            )
            == [salesforce_from_datetime(target)]
        )

        now = datetime.combine(mapping.anchor_date, datetime.now().time())
        assert (
            adjust_relative_dates(
                mapping,
                ([], [0], date.today()),
                [salesforce_from_datetime(now)],
                DataOperationType.INSERT,
            )
            == [salesforce_from_datetime(datetime.combine(date.today(), now.time()))]
        )

        assert adjust_relative_dates(
            mapping, ([], [0], date.today()), [""], DataOperationType.INSERT
        ) == [""]

    def test_relative_datetimes_extract(self):
        mapping = MappingStep(
            sf_object="Account", fields=["Some_Datetime__c"], anchor_date="2020-07-01"
        )

        input_dt = datetime.now() + timedelta(days=7)
        target = datetime.combine(
            mapping.anchor_date + timedelta(days=7), input_dt.time()
        )
        assert (
            adjust_relative_dates(
                mapping,
                ([], [1], date.today()),
                ["001000000000000", salesforce_from_datetime(input_dt)],
                DataOperationType.QUERY,
            )
            == ["001000000000000", salesforce_from_datetime(target)]
        )

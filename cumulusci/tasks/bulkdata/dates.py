from datetime import date, datetime
from typing import List, Optional
from cumulusci.core.config.OrgConfig import OrgConfig
from cumulusci.tasks.bulkdata.step import DataOperationType


def get_relative_date_context(mapping, org_config: OrgConfig):
    fields = mapping.get_field_list()

    date_fields = [
        fields.index(f)
        for f in mapping.get_fields_by_type("date", org_config)
        if f in mapping.fields
    ]
    date_time_fields = [
        fields.index(f)
        for f in mapping.get_fields_by_type("datetime", org_config)
        if f in mapping.fields
    ]

    return (date_fields, date_time_fields)


def adjust_relative_dates(
    mapping,
    context,
    record: List[Optional[str]],
    operation: DataOperationType,
):
    """Convert specified date and time fields (in ISO format) relative to the present moment.
    If some date is 2020-07-30, anchor_date is 2020-07-23, and today's date is 2020-09-01,
    that date will become 2020-09-07 - the same position in the timeline relative to today."""

    date_fields, date_time_fields = context

    # Determine the direction in which we are converting.
    # For extracts, we convert the date from today-anchored to mapping.anchor_date-anchored.
    # For loads, we do the reverse.

    if operation is DataOperationType.QUERY:
        current_anchor = date.today()
        target_anchor = mapping.anchor_date
    else:
        current_anchor = mapping.anchor_date
        target_anchor = date.today()

    r = record.copy()

    for index in date_fields:
        if operation is DataOperationType.QUERY:
            index += 1  # For the Id field.
        if r[index]:
            r[index] = date_to_iso(
                _convert_date(target_anchor, current_anchor, iso_to_date(r[index]))
            )

    for index in date_time_fields:
        if operation is DataOperationType.QUERY:
            index += 1  # For the Id field.
        if r[index]:
            r[index] = salesforce_from_datetime(
                _convert_datetime(
                    target_anchor,
                    current_anchor,
                    datetime_from_salesforce(r[index]),
                )
            )

    return r


# The way Salesforce formats ISO8601 date-times is not quite compatible
# with Python's datetime. Salesforce returns, e.g., "2020-09-14T20:00:17.000+0000",
# while Python wants a : character in the timezone: "2020-09-14T20:00:17.000000+00:00".


def datetime_from_salesforce(d):
    """Create a Python datetime from a Salesforce-style ISO8601 string"""
    # Convert Salesforce's `+0000`, which Python would want as `+00:00`
    return datetime.strptime(d[:-5] + "+00:00", "%Y-%m-%dT%H:%M:%S.%f%z")


def salesforce_from_datetime(d):
    """Create a Salesforce-style ISO8601 string from a Python datetime"""
    # Convert microseconds to milliseconds. Salesforce uses 3 decimals for milliseconds;
    # Python uses 6 for microseconds.
    return d.strftime("%Y-%m-%dT%H:%M:%S.{}+0000").format(str(d.microsecond)[:3])


# Python 3.6 doesn't support the isoformat()/fromisoformat() methods. Shims.


def date_to_iso(d):
    """Convert date object to ISO8601 string"""
    return d.strftime("%Y-%m-%d")


def iso_to_date(s):
    """Convert ISO8601 string to date object"""
    return datetime.strptime(s, "%Y-%m-%d").date()


def _convert_date(target_anchor, current_anchor, this_date):
    """Adjust this_date to be relative to target_anchor instead of current_anchor"""
    return target_anchor + (this_date - current_anchor)


def _convert_datetime(target_anchor, current_anchor, this_datetime):
    """Adjust this_datetime to be relative to target_anchor instead of current_anchor"""
    return datetime.combine(
        _convert_date(target_anchor, current_anchor, this_datetime.date()),
        this_datetime.time(),
    )

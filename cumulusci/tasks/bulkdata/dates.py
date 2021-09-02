from datetime import date, datetime
from typing import List, Optional

from cumulusci.tasks.bulkdata.step import DataOperationType


def adjust_relative_dates(
    mapping,
    context,
    record: List[Optional[str]],
    operation: DataOperationType,
):
    """Convert specified date and time fields (in ISO format) relative to the present moment.
    If some date is 2020-07-30, anchor_date is 2020-07-23, and today's date is 2020-09-01,
    that date will become 2020-09-07 - the same position in the timeline relative to today."""

    date_fields, date_time_fields, today = context

    # Determine the direction in which we are converting.
    # For extracts, we convert the date from today-anchored to mapping.anchor_date-anchored.
    # For loads, we do the reverse.

    if operation is DataOperationType.QUERY:
        current_anchor = today
        target_anchor = mapping.anchor_date
    else:
        current_anchor = mapping.anchor_date
        target_anchor = today

    r = record.copy()

    for index in date_fields:
        if r[index]:
            r[index] = date_to_iso(
                _offset_date(target_anchor, current_anchor, iso_to_date(r[index]))
            )

    for index in date_time_fields:
        if r[index]:
            r[index] = salesforce_from_datetime(
                _offset_datetime(
                    target_anchor,
                    current_anchor,
                    datetime_from_salesforce(r[index]),
                )
            )

    return r


# The Salesforce API returns datetimes with millisecond resolution, but milliseconds
# are always zero (that is, .000). Python does parse this with strptime.
# Python renders datetimes into ISO8601 with microsecond resolution (.123456),
# which Salesforce won't accept - we need exactly three digits, although they are
# currently ignored. Python also right-truncates to `.0`, which Salesforce won't take.
# Hence this clumsy workaround.


def datetime_from_salesforce(d):
    """Create a Python datetime from a Salesforce-style ISO8601 string"""
    return datetime.strptime(d, "%Y-%m-%dT%H:%M:%S.%f%z")


def salesforce_from_datetime(d):
    """Create a Salesforce-style ISO8601 string from a Python datetime"""
    return d.strftime("%Y-%m-%dT%H:%M:%S.{}+0000").format(
        str(d.microsecond)[:3].ljust(3, "0")
    )


# Python 3.6 doesn't support the fromisoformat() method.
# These functions are explicit and work on all supported versions.


def date_to_iso(d):
    """Convert date object to ISO8601 string"""
    return d.strftime("%Y-%m-%d")


def iso_to_date(s):
    """Convert ISO8601 string to date object"""
    if isinstance(s, date):
        return s
    return datetime.strptime(s, "%Y-%m-%d").date()


def _offset_date(target_anchor, current_anchor, this_date):
    """Adjust this_date to be relative to target_anchor instead of current_anchor"""
    return target_anchor + (this_date - current_anchor)


def _offset_datetime(target_anchor, current_anchor, this_datetime):
    """Adjust this_datetime to be relative to target_anchor instead of current_anchor"""
    return datetime.combine(
        _offset_date(target_anchor, current_anchor, this_datetime.date()),
        this_datetime.time(),
    )

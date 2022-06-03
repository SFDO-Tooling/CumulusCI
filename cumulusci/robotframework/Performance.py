from datetime import datetime

from dateutil.parser import ParserError
from dateutil.parser import parse as parse_date
from robot.libraries.BuiltIn import BuiltIn
from robot.utils import timestr_to_secs

from cumulusci.robotframework.base_library import BaseLibrary


class Performance(BaseLibrary):
    """
    Keywords for performance testing.

    For more information on how to use these keywords, see
    the "Performance Testing" section of the CumulusCI documentation.
    """

    def elapsed_time_for_last_record(
        self, obj_name, start_field, end_field, order_by, **kwargs
    ):
        """For records representing jobs or processes, compare the record's start-time to its end-time to see how long a process took.

        Arguments:
            obj_name:   SObject to look for last record
            start_field: Name of the datetime field that represents the process start
            end_field: Name of the datetime field that represents the process end
            order_by: Field name to order by. Should be a datetime field, and usually is just the same as end_field.
            where:  Optional Where-clause to use for filtering
            Other keywords are used for filtering as in the Salesforce Query keywordf

        The last matching record queried and summarized.

        Example:

            | ${time_in_seconds} =    Elapsed Time For Last Record
            | ...             obj_name=AsyncApexJob
            | ...             where=ApexClass.Name='BlahBlah'
            | ...             start_field=CreatedDate
            | ...             end_field=CompletedDate
            | ...             order_by=CompletedDate
        """
        if len(order_by.split()) != 1:
            raise Exception("order_by should be a simple field name")
        query = self.salesforce_api._soql_query_builder(
            obj_name,
            select=f"{start_field}, {end_field}",
            order_by=order_by + " DESC NULLS LAST",
            limit=1,
            **kwargs,
        )
        response = self.salesforce_api.soql_query(query)
        results = response["records"]

        if results:
            record = results[0]
            return _duration(record[start_field], record[end_field], record)
        else:
            raise Exception(f"Matching record not found: {query}")

    def start_performance_timer(self):
        """Start an elapsed time stopwatch for performance tests.

        See the docummentation for **Stop Performance Timer** for more
        information.

        Example:

        | Start Performance Timer
        | Do Something
        | Stop Performance Timer
        """
        BuiltIn().set_test_variable("${__start_time}", datetime.now())

    def stop_performance_timer(self):
        """Record the results of a stopwatch. For perf testing.

        This keyword uses Set Test Elapsed Time internally and therefore
        outputs in all of the ways described there.

        Example:

        | Start Performance Timer
        | Do Something
        | Stop Performance Timer

        """
        start_time = self.builtin.get_variable_value("${__start_time}")
        if start_time:
            seconds = (datetime.now() - start_time).seconds
            assert seconds is not None
            self.set_test_elapsed_time(seconds)
        else:
            raise Exception(
                "Elapsed time clock was not started. "
                "Use the Start Elapsed Time keyword to do so."
            )

    def set_test_elapsed_time(self, elapsedtime):
        """This keyword captures a computed rather than measured elapsed time for performance tests.

        For example, if you were performance testing a Salesforce batch process, you might want to
        store the Salesforce-measured elapsed time of the batch process instead of the time measured
        in the CCI client process.

        The keyword takes a single argument which is either a number of seconds or a Robot time string
        (https://robotframework.org/robotframework/latest/libraries/DateTime.html#Time%20formats).

        Using this keyword will automatically add the tag cci_metric_elapsed_time to the test case
        and ${cci_metric_elapsed_time} to the test's variables. cci_metric_elapsed_time is not
        included in Robot's html statistical roll-ups.

        Example:

        | Set Test Elapsed Time       11655.9

        Performance test times are output in the CCI logs and are captured in MetaCI instead of the
        "total elapsed time" measured by Robot Framework. The Robot "test message" is also updated."""

        try:
            seconds = float(elapsedtime)
        except ValueError:
            seconds = timestr_to_secs(elapsedtime)
        assert seconds is not None

        self.builtin.set_test_message(f"Elapsed time set by test : {seconds}")
        self.builtin.set_tags("cci_metric_elapsed_time")
        self.builtin.set_test_variable("${cci_metric_elapsed_time}", seconds)

    def set_test_metric(self, metric: str, value=None):
        """This keyword captures any metric for performance monitoring.

        For example: number of queries, rows processed, CPU usage, etc.

        The keyword takes a metric name, which can be any string, and a value, which
        can be any number.

        Using this keyword will automatically add the tag cci_metric to the test case
        and ${cci_metric_<metric_name>} to the test's variables. These permit downstream
        processing in tools like CCI and MetaCI.

        cci_metric is not included in Robot's html statistical roll-ups.

        Example:

        | Set Test Metric    Max_CPU_Percent    30

        Performance test metrics are output in the CCI logs, log.html and output.xml.
        MetaCI captures them but does not currently have a user interface for displaying
        them."""

        value = float(value)

        self.builtin.set_tags("cci_metric")
        self.builtin.set_test_variable("${cci_metric_%s}" % metric, value)


def _duration(start_date: str, end_date: str, record: dict):
    try:
        start_date = parse_date(start_date)
        end_date = parse_date(end_date)
    except (ParserError, TypeError) as e:
        raise Exception(f"Date parse error: {e} in record {record}")
    duration = end_date - start_date
    return duration.total_seconds()

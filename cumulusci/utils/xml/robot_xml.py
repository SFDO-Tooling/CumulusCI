import re
from typing import Callable, Dict, NamedTuple

from robot.api import ExecutionResult, ResultVisitor  # type: ignore
from robot.result.model import TestCase

UNITS = {
    "setup_time": ("s", "Setup Time"),
    "teardown_time": ("s", "Teardown Time"),
    "total_time": ("s", "Total Time"),
    "elapsed_time": ("s", "Elapsed Time"),
}


class PerfSummary(NamedTuple):
    name: str
    metrics: Dict[str, float]
    test: TestCase


def _format_metric(metric_name: str, value: float) -> str:
    "Format a metric value for output"
    extra_info = UNITS.get(metric_name)
    if extra_info:
        unit, name = extra_info
    else:
        unit, name = "", metric_name
    return f"{name}: {value}{unit} "


def _perf_formatter(perfsummary: PerfSummary) -> str:
    """Default formatter for perf summaries"""

    other_metrics = [
        _format_metric(metric, value)
        for metric, value in perfsummary.metrics.items()
        if metric != "total_time"
    ]

    result = f"{perfsummary.name} - "

    if other_metrics:
        other_metrics = ", ".join(other_metrics)
        result += other_metrics

    return result


def log_perf_summary_from_xml(
    robot_xml, logger_func: Callable, formatter_func: Callable = _perf_formatter
):
    """Log Robot performance info to a callable which accepts a string.

    Supply a formatter that takes a PerfSummary triple if the default isn't a good fit:

        f(test_name: str, metrics: Dict[str, float], test: robot.result.model.TestCase)
    """
    result = ExecutionResult(robot_xml)
    pl = _perf_logger(logger_func, formatter_func)
    next(pl)  # start the generator
    perf_summarizer = PerfSummarizer(pl.send)
    result.visit(perf_summarizer)


def _perf_logger(logger_func: Callable, formatter_func: Callable):
    """Generator that connects visitor to logger"""
    # ensure we have at least one result before printing header
    perfsummary = yield
    logger_func(" === Performance Results  === ")

    while perfsummary:
        logger_func(formatter_func(perfsummary))
        perfsummary = yield


pattern = r"\${cci_metric_(?P<metric>.*)} = (?P<value>.*)"
# used also in MetaCI
ELAPSED_TIME_PATTERN = re.compile(pattern)


class PerfSummarizer(ResultVisitor):
    """Robot ResultVisitor that looks for performance summaries"""

    def __init__(self, callable):
        self.times = []
        self.callable = callable

    def start_test(self, test):
        self.metrics = {}

    def end_message(self, message):
        # n.b. we're looking for messages like '${cci_metric_foo} = x'
        match = ELAPSED_TIME_PATTERN.match(message.message)
        if match:
            try:
                self.metrics[match["metric"]] = float(match["value"])
            except ValueError as e:  # pragma: no cover
                raise ValueError(  # -- should never happen
                    f"Cannot find number in {message.message}"
                ) from e

    def end_test(self, test):
        if self.metrics:
            self.report_test_metrics(test, self.metrics)

    def report_test_metrics(self, test, metrics):
        "Generate a perf summary and call formatter&logger to output it"
        if test.setup:
            metrics["setup_time"] = test.setup.elapsedtime / 1000
        if test.teardown:
            metrics["teardown_time"] = test.teardown.elapsedtime / 1000
        metrics["total_time"] = test.elapsedtime / 1000

        self.callable(PerfSummary(test.name, metrics, test))

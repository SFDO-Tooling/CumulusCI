from typing import Callable, NamedTuple, Dict
import re

from robot.api import ExecutionResult, ResultVisitor
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

        f(test_name: str, metrics: Dict[str, float], test: robot.result.model.TestCase)"""
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


class PerfSummarizer(ResultVisitor):
    """Robot ResultVisitor that looks for performance summaries"""

    def __init__(self, callable):
        self.times = []
        self.callable = callable

    def end_test(self, test):
        metrics = {}
        for keyword in test.keywords:
            if keyword:
                for message in keyword.messages:
                    message = str(message or "")
                    if message:
                        match = re.match(pattern, message)
                        if match:
                            try:
                                metrics[match["metric"]] = float(match["value"])
                            except ValueError as e:  # pragma: no cover
                                raise ValueError(  # -- should never happen
                                    f"Cannot find number in {message}"
                                ) from e
        if metrics:
            self.report_test_metrics(test, metrics)

    def report_test_metrics(self, test, metrics):
        "Generate a perf summary and call formatter&logger to output it"
        setup_keyword = test.keywords.setup
        if setup_keyword:
            metrics["setup_time"] = setup_keyword.elapsedtime / 1000
        teardown_keyword = test.keywords.teardown
        if teardown_keyword:
            metrics["teardown_time"] = teardown_keyword.elapsedtime / 1000
        metrics["total_time"] = test.elapsedtime / 1000

        self.callable(PerfSummary(test.name, metrics, test))

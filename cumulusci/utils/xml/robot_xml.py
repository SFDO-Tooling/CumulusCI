from typing import NamedTuple, Callable, Optional

from robot.api import ExecutionResult, ResultVisitor


class PerfTestSummary(NamedTuple):
    name: str
    setup_time: Optional[float]
    teardown_time: Optional[float]
    total_test_time: float
    specified_test_time: Optional[float]


def _perf_formatter(perfsummary):
    """Default formatter for perf summaries as strings"""
    setup_time = (
        f"setup: {round(perfsummary.setup_time, 2)}s, "
        if perfsummary.setup_time
        else ""
    )
    teardown_time = (
        f"teardown: {round(perfsummary.teardown_time, 2)}s, "
        if perfsummary.teardown_time
        else ""
    )
    total_time = f"total: {round(perfsummary.total_test_time, 2)}s"
    time = f"{perfsummary.specified_test_time} seconds"
    return f"{perfsummary.name} reported elapsed time: {time} ({setup_time}{teardown_time}{total_time})"


def log_perf_summary_from_xml(
    robot_xml, logger_func: Callable, formatter_func: Callable = _perf_formatter
):
    """Log Robot performance info to a callable which accepts a string.

    Supply a formatter that converts PerfTestSummary 5-tuples to strings
    if the default isn't a good fit."""
    result = ExecutionResult(robot_xml)
    pl = _perf_logger(logger_func, formatter_func)
    next(pl)  # start the generator
    perf_summarizer = PerfSummarizer(pl.send)
    result.visit(perf_summarizer)


def _perf_logger(logger_func: Callable, formatter_func: Callable):
    """Generator that connects visitor to logger"""
    perfsummary = yield
    logger_func(" === Performance Results  === ")

    while perfsummary:
        logger_func(formatter_func(perfsummary))
        perfsummary = yield


prefix = "${specified_elapsed_time} = "


class PerfSummarizer(ResultVisitor):
    """Robot ResultVisitor that looks for performance summaries"""

    def __init__(self, callable):
        self.times = []
        self.callable = callable

    def end_test(self, test):
        for keyword in test.keywords:
            if keyword:
                for message in keyword.messages:
                    message = str(message or "")
                    if message:
                        if message.startswith(prefix):
                            self.report_message(test, message)
                            break  # just use the first one

    def report_message(self, test, message):
        time = message[len(prefix) :]
        setup_keyword = test.keywords.setup
        teardown_keyword = test.keywords.teardown
        self.callable(
            PerfTestSummary(
                test.name,
                setup_keyword.elapsedtime / 1000 if setup_keyword else None,
                teardown_keyword.elapsedtime / 1000 if teardown_keyword else None,
                test.elapsedtime / 1000,
                float(time),
            )
        )

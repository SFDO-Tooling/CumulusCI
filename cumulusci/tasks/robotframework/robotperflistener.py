import os
import json
import time


def mean(numbers):
    return float(sum(numbers)) / max(len(numbers), 1)


class TestMetrics:
    """Manage both REST API (predefined) metrics and also custom metrics"""

    def __init__(self):
        self.api_metrics = []
        self.custom_metrics = {}

    def summarize(self):
        collections = {}
        for metricset in self.api_metrics:
            assert isinstance(metricset, dict), metricset
            for name, value in metricset.items():
                if not name.startswith("_"):
                    collections.setdefault(name, []).append(float(value))

        aggregations = {}
        for metric_name, metricset in collections.items():
            aggregations[metric_name + "-sum"] = sum(metricset)
            aggregations[metric_name + "-avg"] = mean(metricset)

        return aggregations


class RobotPerfListener:
    """A robot listener for performance metrics from REST APIs and other code"""

    ROBOT_LISTENER_API_VERSION = 2

    def __init__(self, task, verbosity):
        self._metrics = {}
        self.task = task
        self.verbosity = verbosity
        self.outputdir = None

    def start_suite(self, name, attributes=None):
        self._current_suite = {}
        self._metrics[name] = self._current_suite

    def end_suite(self, name, attributes=None):
        self._current_suite = None

    def start_test(self, name, attributes=None):
        self._current_test = TestMetrics()

    def end_test(self, name, attributes=None):
        totals = self._current_test.summarize()
        totals.update(
            {
                name: metric.value
                for name, metric in self._current_test.custom_metrics.items()
            }
        )

        test_result = {"totals": dict(sorted(totals.items()))}

        if self.verbosity >= 1:
            test_result["traces"] = self._current_test.api_metrics

        self._current_suite[name] = test_result
        self._current_test = None

    def close(self):
        filename = os.path.join(self.outputdir, "perf.json")
        with open(filename, "w") as f:
            json.dump(self._metrics, f, indent=2)

        # cleanup so we won't be called again and also remove GC loop
        self.task.robot_perf_listener = None
        self.task = None

    def output_file(self, path):
        self.outputdir = os.path.dirname(path)

    def report(self, metrics):
        """Extension to the Listener API for reporting custom metrics."""
        if self._current_test:  # sometimes we are called in suite teardown
            self._current_test.api_metrics.append(metrics)

    def create_aggregate_metric(self, name, aggregation):
        """Extension to the Listener API for creating new aggregate metrics (.e.g. averages, sums)."""
        self._current_test.custom_metrics[name] = Aggregations[aggregation]()

    def store_metric_value(self, name, value):
        """Extension to the Listener API for adding new values to a metric."""
        self._current_test.custom_metrics[name].process(value)

    def create_duration_metric(self, name):
        """Extension to the Listener API for creating new durations."""
        self._current_test.custom_metrics[name] = DurationAggregator()

    def end_duration_metric(self, name):
        """Extension to the Listener API for finishing durations."""
        metric_obj = self._current_test.custom_metrics[name]
        metric_obj.finish()


class AverageAggregator:
    """Takes a stream of numbers delivered to the "reduce" function and averages them"""

    def __init__(self):
        self.sum = 0
        self.count = 0

    def process(self, value):
        self.sum += float(value)
        self.count += 1

    @property
    def value(self):
        return self.sum / self.count


class TotalAggregator:
    """Takes a stream of numbers delivered to the "reduce" function and sums them"""

    def __init__(self):
        self.value = 0

    def process(self, value):
        self.value += value


class DurationAggregator:
    """Figures out how long it takes to run some Robot code"""

    def __init__(self):
        self.start_time = time.time()
        self.duration = -1

    def process(self, value):
        pass

    def finish(self):
        self.duration = time.time() - self.start_time

    @property
    def value(self):
        return self.duration


Aggregations = {
    "duration": DurationAggregator,
    "average": AverageAggregator,
    "sum": TotalAggregator,
}

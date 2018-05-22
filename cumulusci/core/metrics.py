""" CumulusCI supports tasks emitting metrics. 

Metrics are emitted by tasks, collated by CumulusCI during flow execution, 
and then made available in the flow results for the flowrunner (CLI or MetaCI) to analyze. 

The final metric output includes the commit hash or ref. I'll have to dig into the config
to figure out where that suff is, because in CI its injected by the environment.

A task can emit `n` metrics which are a python dict representation of a StatsD metric:
```
{
    'bucket':'contactInsert.totalTime',
    'value':'350', 
    'type': 'ms'
}
```

Each metric has a bucket name, type, and a value. Bucket names do not need to be predefined,
but all values for a given bucket should have the same type. Bucket value is a string representation
of an integer.

CCI Metrics do not support StatsD sampling.

The flow runner will collect all metrics from the task instances, and then act on them
as desired. The BaseFlow runner will output them to a flat file. The MetaCIFlow runner
could import them into django models.

First, we'll add a metrics collection to BaseTask, and define an emitter.

BaseTask._emit_event(metric_bucket, metric_type, metric_value)
BaseTask.metrics = {}

"""

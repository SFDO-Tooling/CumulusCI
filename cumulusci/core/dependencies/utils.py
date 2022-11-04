from collections import namedtuple

# data structure mimicking a task for use with the metadata API classes
TaskContext = namedtuple("TaskContext", ["org_config", "project_config", "logger"])

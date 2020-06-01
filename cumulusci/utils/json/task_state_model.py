from .model_parser import CCIModel


class TaskStateModel(CCIModel):
    def __init__(self, task_state_filename, *args, **kwargs):
        self._filename = task_state_filename
        super.__init__(*args, **kwargs)

    def save(self):
        with open(self._filename, "w") as f:
            f.write(self.json(indent=2))

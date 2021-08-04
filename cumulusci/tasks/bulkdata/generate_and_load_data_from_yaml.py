from cumulusci.tasks.bulkdata import GenerateAndLoadData
from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateDataFromYaml

bulkgen_task = "cumulusci.tasks.bulkdata.generate_from_yaml.GenerateDataFromYaml"


# Class to glue together the task_options from GenerateAndLoadData
# and GenerateDataFromYaml
class GenerateAndLoadDataFromYaml(GenerateAndLoadData):
    """Generate and load data from Snowfakery in as many batches as necessary"""

    task_options = {
        **GenerateAndLoadData.task_options,
        **GenerateDataFromYaml.task_options,
    }

    def _init_options(self, kwargs):
        args = {"data_generation_task": bulkgen_task, **kwargs}
        super()._init_options(args)

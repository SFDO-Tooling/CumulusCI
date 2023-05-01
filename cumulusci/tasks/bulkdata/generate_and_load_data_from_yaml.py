from unittest import mock

from cumulusci.tasks.bulkdata import GenerateAndLoadData
from cumulusci.tasks.bulkdata.generate_from_yaml import GenerateDataFromYaml
from cumulusci.tasks.bulkdata import mapping_parser


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

    def _run_task(self, *args, **kwargs):
        with _disable_confusing_record_type_warning():
            super()._run_task(*args, **kwargs)


def _disable_confusing_record_type_warning():
    """
    Currently Snowfakery uses a feature that is technically deprecated
    in mapping files. CumulusCI "warns" the user not to use a feature
    that they didn't mean to use.

    https://github.com/SFDO-Tooling/CumulusCI/issues/2093

    This is a bit of a hack but doing it "right" is fairly hard with
    Pydantic and all of the layers of CumulusCI and the hack seems
    pretty low risk. The correct option would need to be threaded
    through about 6-8 layers of CumulusCI/Pydantic stack frames.

    Also the whole thing should be fixed in a better way some time
    in 2021: CumulusCI should support record names in a column rather
    than just indirected record IDs. Then Snowfakery will just
    output the record names in an intuitive fashion.
    """

    # not thread-safe but hardly anything in CumulusCI is.
    return mock.patch.object(
        mapping_parser,
        "SHOULD_REPORT_RECORD_TYPE_DEPRECATION",
        False,
    )

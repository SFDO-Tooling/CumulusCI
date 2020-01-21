from cumulusci.tasks.bulkdata.delete import DeleteData
from cumulusci.tasks.bulkdata.extract import ExtractData
from cumulusci.tasks.bulkdata.generate_mapping import GenerateMapping
from cumulusci.tasks.bulkdata.load import LoadData
from cumulusci.tasks.bulkdata.generate_and_load_data import GenerateAndLoadData

# For backwards-compatibility
QueryData = ExtractData
__all__ = (
    "DeleteData",
    "ExtractData",
    "GenerateMapping",
    "LoadData",
    "GenerateAndLoadData",
)

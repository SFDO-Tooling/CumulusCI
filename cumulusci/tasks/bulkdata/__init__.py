from cumulusci.tasks.bulkdata.delete import DeleteData  # noqa: F401
from cumulusci.tasks.bulkdata.extract import ExtractData
from cumulusci.tasks.bulkdata.generate import GenerateMapping  # noqa: F401
from cumulusci.tasks.bulkdata.load import LoadData  # noqa: F401

# For backwards-compatibility
QueryData = ExtractData

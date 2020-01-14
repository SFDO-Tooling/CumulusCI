from cumulusci.tasks.bulkdata.base_generate_data_task import BaseGenerateDataTask


class GenerateDummyData(BaseGenerateDataTask):
    """Generate data based on test mapping.yml"""

    def _read_mappings(self, mapping_file_path):
        assert mapping_file_path is None
        return None

    def generate_data(*args, **kwargs):
        return None

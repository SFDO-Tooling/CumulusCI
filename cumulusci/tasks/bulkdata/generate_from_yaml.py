import os

import yaml

from cumulusci.core.utils import process_list_of_pairs_dict_arg

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.bulkdata.base_generate_data_task import BaseGenerateDataTask
from snowfakery.output_streams import SqlOutputStream
from snowfakery.data_generator import generate
from snowfakery.generate_mapping_from_factory import mapping_from_factory_templates


class GenerateDataFromYaml(BaseGenerateDataTask):
    """Generate sample data from a YAML template file."""

    task_docs = """
    Depends on the currently un-released Snowfakery tool from SFDO. Better documentation
    will appear here when Snowfakery is publically available.
    """

    task_options = {
        **BaseGenerateDataTask.task_options,
        "generator_yaml": {
            "description": "A generator YAML file to use",
            "required": True,
        },
        "vars": {
            "description": "Pass values to override options in the format VAR1:foo,VAR2:bar"
        },
        "generate_mapping_file": {
            "description": "A path to put a mapping file inferred from the generator_yaml",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        self.yaml_file = os.path.abspath(self.options["generator_yaml"])
        if not os.path.exists(self.yaml_file):
            raise TaskOptionsError(f"Cannot find {self.yaml_file}")
        if "vars" in self.options:
            self.vars = process_list_of_pairs_dict_arg(self.options["vars"])
        else:
            self.vars = {}
        self.generate_mapping_file = self.options.get("generate_mapping_file")
        if self.generate_mapping_file:
            self.generate_mapping_file = os.path.abspath(self.generate_mapping_file)

    def _generate_data(self, db_url, mapping_file_path, num_records, current_batch_num):
        """Generate all of the data"""
        if mapping_file_path:
            with open(mapping_file_path, "r") as f:
                self.mappings = yaml.safe_load(f)
        else:
            self.mappings = {}
        session, engine, base = self.init_db(db_url, self.mappings)
        self.generate_data(session, engine, base, num_records, current_batch_num)
        session.commit()
        session.close()

    def generate_data(self, session, engine, base, num_records, current_batch_num):
        output_stream = SqlOutputStream.from_connection(
            session, engine, base, self.mappings
        )
        with open(self.yaml_file) as open_yaml_file:
            summary = generate(
                open_yaml_file, self.num_records, self.vars, output_stream
            )
            output_stream.close()
            if self.generate_mapping_file:
                with open(self.generate_mapping_file, "w+") as f:
                    yaml.safe_dump(
                        mapping_from_factory_templates(summary), f, sort_keys=False
                    )
                    f.close()

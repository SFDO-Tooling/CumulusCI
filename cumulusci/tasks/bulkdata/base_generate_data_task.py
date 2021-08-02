import os
from abc import ABCMeta, abstractmethod

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import create_session

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.tasks import BaseTask
from cumulusci.tasks.bulkdata.mapping_parser import parse_from_yaml

from .utils import create_table


class BaseGenerateDataTask(BaseTask, metaclass=ABCMeta):
    """Abstract base class for any class that generates data in a SQL DB."""

    task_docs = """
    Use the `num_records` option to specify how many records to generate.
    Use the `mapping` option to specify a mapping file.
    """

    task_options = {
        "num_records": {
            "description": "How many records to generate: total number of opportunities.",
            "required": False,
        },
        "mapping": {"description": "A mapping YAML file to use", "required": False},
        "database_url": {
            "description": "A path to put a copy of the sqlite database (for debugging)",
            "required": False,
        },
    }

    def _init_options(self, kwargs):
        super()._init_options(kwargs)
        if self.options.get("mapping"):
            self.mapping_file = os.path.abspath(self.options["mapping"])
        else:
            self.mapping_file = None
        self.database_url = self.options.get("database_url")
        self.current_batch_num = self.options.get("current_batch_number", 0)
        if not self.database_url:
            sqlite_path = "generated_data.db"
            self.logger.info("No database URL: creating sqlite file %s" % sqlite_path)
            self.database_url = "sqlite:///" + sqlite_path

        num_records = self.options.get("num_records")
        self.num_records = int(num_records) if num_records is not None else None

    def _run_task(self):
        self._generate_data(
            self.database_url,
            self.mapping_file,
            self.num_records,
            self.current_batch_num,
        )

    def _generate_data(
        self,
        db_url: str,
        mapping_file_path: str = None,
        num_records: int = None,
        current_batch_num=0,
    ):
        """Generate all of the data"""
        mappings = self._read_mappings(mapping_file_path)
        session, engine, base = self.init_db(db_url, mappings)
        self.generate_data(session, engine, base, num_records, current_batch_num)
        session.commit()

    def _read_mappings(self, mapping_file_path):
        if not mapping_file_path:
            raise TaskOptionsError("Mapping file path required")

        return parse_from_yaml(mapping_file_path)

    @staticmethod
    def init_db(db_url, mappings):
        engine = create_engine(db_url)
        metadata = MetaData()
        metadata.bind = engine
        if mappings:
            for name, mapping in mappings.items():
                if "table" in mapping and mapping["table"] not in metadata.tables:
                    create_table(mapping, metadata)
        metadata.create_all()
        base = automap_base(bind=engine, metadata=metadata)
        base.prepare(engine, reflect=True)
        session = create_session(bind=engine, autocommit=False)
        return session, engine, base

    @abstractmethod
    def generate_data(self, session, engine, base, num_records, current_batch_num):
        """Abstract methods for base classes to really generate
        the data into an open session."""

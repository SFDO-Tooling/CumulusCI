import yaml
from sqlalchemy import MetaData, Table, create_engine, func, select


class SnowfakeryWorkingDirectory:
    """Helper functions based on well-known filenames in CCI/Snowfakery working directories."""

    def __init__(self, working_dir):
        self.path = working_dir
        self.mapping_file = working_dir / "temp_mapping.yml"
        self.database_file = working_dir / "generated_data.db"
        assert self.mapping_file.exists(), self.mapping_file
        assert self.database_file.exists(), self.database_file
        self.database_url = f"sqlite:///{self.database_file}"
        self.continuation_file = f"{working_dir}/continuation.yml"

    def setup_engine(self):
        """Set up the database engine"""
        engine = create_engine(self.database_url)

        metadata = MetaData(engine)
        metadata.reflect()
        return engine, metadata

    @property
    def index(self) -> str:
        return self.path.name.rsplit("_")[0]

    def get_record_counts(self):
        """Get record counts generated for this portion."""
        engine, metadata = self.setup_engine()

        with engine.connect() as connection:
            record_counts = {
                table_name: self._record_count_from_db(connection, table)
                for table_name, table in metadata.tables.items()
                if table_name[-6:] != "sf_ids"
            }
        # note that the template has its contents deleted so if the cache
        # is ever removed, it will start to return {}
        assert record_counts
        return record_counts

    def _record_count_from_db(self, connection, table: Table):
        """Count rows in a table"""
        stmt = select(func.count()).select_from(table)
        result = connection.execute(stmt)
        return next(result)[0]

    def relevant_sobjects(self):
        with open(self.mapping_file, encoding="utf-8") as f:
            mapping = yaml.safe_load(f)
            return [m.get("sf_object") for m in mapping.values() if m.get("sf_object")]

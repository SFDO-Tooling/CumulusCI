from cumulusci.tasks.bulkdata.base_generate_data_task import (
    create_table as create_table_from_mapping,
)
from abc import abstractmethod, ABC
from sqlalchemy import create_engine, MetaData, Column, Integer, Table, Unicode
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import create_session
from .data_gen_exceptions import DataGenError


class OutputStream(ABC):
    count = 0
    flush_limit = 1000

    def create_or_validate_tables(self, tables):
        pass

    def write_row(self, tablename, row):
        self.write_single_row(tablename, row)
        if self.count > self.flush_limit:
            self.flush()
            self.count = 0
        self.count += 1

    @abstractmethod
    def write_single_row(self, tablename, row):
        pass


class DebugOutputStream(OutputStream):
    def write_single_row(self, tablename, row):
        values = ", ".join([f"{key}={value}" for key, value in row.items()])
        print(f"{tablename}({values})")


class SqlOutputStream(OutputStream):
    mappings = None

    @classmethod
    def from_url(cls, db_url, mappings):
        self = cls()
        self.mappings = mappings
        self.engine = create_engine(db_url)
        self._init_db()
        return self

    @classmethod
    def from_connection(cls, session, engine, base):
        self = cls()
        self.session = session
        self.engine = engine
        self.base = base
        self._init_db()
        return self

    def _init_db(self):
        self.metadata = MetaData()
        self.metadata.bind = self.engine

    def write_single_row(self, tablename, row):
        model = self.metadata.tables[tablename]
        ins = model.insert().values(**row)
        self.session.execute(ins)
        self.session.commit()

    def flush(self):
        self.session.flush()

    def close(self):
        self.session.commit()
        self.session.close()

    def create_or_validate_tables(self, tables):
        if self.mappings:
            _validate_fields(self.mappings, tables)
            for mapping in self.mappings.values():
                create_table_from_mapping(mapping, self.metadata)
        else:
            create_tables_from_inferred_fields(tables, self.engine, self.metadata)
        self.metadata.create_all()
        self.base = automap_base(bind=self.engine, metadata=self.metadata)
        self.base.prepare(self.engine, reflect=True)
        self.session = create_session(bind=self.engine, autocommit=False)


def _validate_fields(mappings, tables):
    """Validate that the field names detected match the mapping"""
    pass  # TODO


def create_tables_from_inferred_fields(tables, engine, metadata):
    """Create tables based on dictionary of tables->field-list."""
    for table_name, table in tables.items():
        columns = [Column(field_name, Unicode(255)) for field_name in table.fields]
        id_column = Column("id", Integer(), primary_key=True, autoincrement=True)

        t = Table(table_name, metadata, id_column, *columns)
        if t.exists():
            raise DataGenError(f"Table already exists: {table_name}", None, None)

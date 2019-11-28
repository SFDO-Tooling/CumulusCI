import os
from abc import abstractmethod, ABC
import json
import csv
import datetime
from urllib.parse import urlparse
from pathlib import Path
from collections import namedtuple, defaultdict

from sqlalchemy import create_engine, MetaData, Column, Integer, Table, Unicode
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import create_session
from .data_gen_exceptions import DataGenError

from cumulusci.tasks.bulkdata.base_generate_data_task import (
    create_table as create_table_from_mapping,
)

from cumulusci.tasks.bulkdata.data_generation.data_generator_runtime import ObjectRow
from faker.utils.datetime_safe import date as fake_date, datetime as fake_datetime


def noop(x):
    return x


class OutputStream(ABC):
    count = 1
    flush_limit = 1000
    commit_limit = 10000
    encoders = {
        str: str,
        int: int,
        float: float,
        datetime.date: noop,
        datetime.datetime: noop,
        fake_date: lambda x: datetime.date(year=x.year, month=x.month, day=x.day),
        fake_datetime: lambda x: datetime.datetime(
            year=x.year,
            month=x.month,
            day=x.day,
            hour=x.hour,
            minute=x.minute,
            second=x.second,
            microsecond=x.microsecond,
            tzinfo=x.tzinfo,
        ),
        type(None): noop,
    }

    def create_or_validate_tables(self, tables):
        pass

    def flatten(self, sourcetable, fieldname, row, obj):
        return obj.id

    def flush(self):
        pass

    def commit(self):
        pass

    def cleanup(self, field_name, field_value, sourcetable, row):
        if isinstance(field_value, ObjectRow):
            return self.flatten(sourcetable, field_name, row, field_value)
        else:
            encoder = self.encoders.get(type(field_value))
            if not encoder:
                raise TypeError(
                    f"No encoder found for {type(field_value)} in {self.__class__.__name__} "
                    f"for {field_name}, {field_value} in {sourcetable}"
                )
            return encoder(field_value)

    def write_row(self, tablename, row_with_references):
        row_cleaned_up_and_flattened = {
            field_name: self.cleanup(
                field_name, field_value, tablename, row_with_references
            )
            for field_name, field_value in row_with_references.items()
        }
        self.write_single_row(tablename, row_cleaned_up_and_flattened)
        if self.count % self.flush_limit == 0:
            self.flush()

        if self.count % self.commit_limit == 0:
            self.commit()

        self.count += 1

    @abstractmethod
    def write_single_row(self, tablename, row):
        """Write a single row to the stream"""
        pass

    def close(self):
        """Close any resources the stream opened.

        Do not close file handles which were passed in!
        """
        pass


class DebugOutputStream(OutputStream):
    def write_single_row(self, tablename, row):
        values = ", ".join([f"{key}={value}" for key, value in row.items()])
        print(f"{tablename}({values})")

    def flatten(self, sourcetable, fieldname, row, obj):
        return f"{obj._tablename}({obj.id})"


CSVContext = namedtuple("CSVContext", ["dictwriter", "file"])


class CSVOutputStream(OutputStream):
    def __init__(self, url):
        super().__init__()

        parts = urlparse(url)
        self.target_path = Path(parts.path)
        if not os.path.exists(self.target_path):
            os.makedirs(self.target_path)

    def open_writer(self, table_name, table):
        file = open(self.target_path / f"{table_name}.csv", "w")
        writer = csv.DictWriter(file, list(table.fields.keys()) + ["id"])
        writer.writeheader()
        return CSVContext(dictwriter=writer, file=file)

    def create_or_validate_tables(self, tables):
        self.writers = {
            table_name: self.open_writer(table_name, table)
            for table_name, table in tables.items()
        }

    def write_single_row(self, tablename, row):
        self.writers[tablename].dictwriter.writerow(row)

    def close(self):
        for context in self.writers.values():
            context.file.close()

        table_metadata = [
            {"url": f"{table_name}.csv"} for table_name, writer in self.writers.items()
        ]
        csv_metadata = {
            "@context": "http://www.w3.org/ns/csvw",
            "tables": table_metadata,
        }
        csvw_filename = self.target_path / "csvw_metadata.json"
        with open(csvw_filename, "w") as f:
            json.dump(csv_metadata, f, indent=2)


class JSONOutputStream(OutputStream):
    encoders = {
        **OutputStream.encoders,
        datetime.date: str,
        datetime.datetime: str,
        fake_date: str,
        fake_datetime: str,
    }

    def __init__(self, file):
        assert file
        self.file = file
        self.first_row = True

    def write_single_row(self, tablename, row):
        if self.first_row:
            self.file.write("[")
            self.first_row = False
        else:
            self.file.write(",\n")
        values = {"_table": tablename, **row}
        self.file.write(json.dumps(values))

    def close(self):
        self.file.write("]\n")


class FallbackDict(dict):
    """Make sure every row has the same records per SQLAlchemy's rules

    According to the SQL Alchemy docs, every dictionary in a set must
    have the same keys. This dict subclass "virtually" expands them
    all to include missing columns.

    This means that the INSERT statement will be more bloated but it
    seems much more efficient than line-by-line inserts.
    """

    def __init__(self, sparse_dict, fallback_dict):
        self.sparse_dict = sparse_dict
        self.fallback_dict = fallback_dict

    def __contains__(self, value):
        # Fallback dict has a superset of keys by definition.
        return value in self.fallback_dict

    def __getitem__(self, name):
        # Sparse dict has all of the "real" items
        return self.sparse_dict.get(name, None)

    def keys(self):
        # Fallback dict has a superset of keys by definition.
        return self.fallback_dict.keys()

    def __bool__(self):
        return True  # Rows are never empty. They always have an ID


class SqlOutputStream(OutputStream):
    mappings = None

    @classmethod
    def from_url(cls, db_url, mappings):
        self = cls()
        self.mappings = mappings
        self.engine = create_engine(db_url)
        self.buffered_rows = defaultdict(list)
        self.table_info = {}
        self._init_db()
        return self

    @classmethod
    def from_connection(cls, session, engine, base):
        self = cls()
        self.session = session
        self.engine = engine
        self.base = base
        self._init_db()
        self.buffered_rows = defaultdict(list)

        return self

    def _init_db(self):
        self.metadata = MetaData()
        self.metadata.bind = self.engine

    def write_single_row(self, tablename, row):
        # cache the value for later insert
        self.buffered_rows[tablename].append(row)

    def flush(self):
        for tablename, (insert_statement, fallback_dict) in self.table_info.items():
            values = [
                FallbackDict(row, fallback_dict)
                for row in self.buffered_rows[tablename]
            ]
            if values:
                self.session.execute(insert_statement, values)
            self.buffered_rows[tablename] = []
        self.session.flush()

    def commit(self):
        self.flush()
        self.session.commit()

    def close(self):
        self.commit()
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

        # Setup table info used by the write-buffering infrastructure
        TableTuple = namedtuple("TableTuple", ["insert_statement", "fallback_dict"])

        for tablename, model in self.metadata.tables.items():
            self.table_info[tablename] = TableTuple(
                insert_statement=model.insert(bind=self.engine, inline=True),
                fallback_dict={key: None for key in tables[tablename].fields.keys()},
            )


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
            raise DataGenError(
                f"Table already exists: {table_name} in {engine.url}", None, None
            )


class GraphvizOutputStream(OutputStream):
    def __init__(self, file):
        super().__init__()
        import pygraphviz

        self.G = pygraphviz.AGraph(strict=False, directed=True)
        self.G.edge_attr["fontsize"] = "10"
        self.G.node_attr["style"] = "filled"
        self.G.node_attr["fillcolor"] = "#1798c1"
        self.G.node_attr["fontcolor"] = "#FFFFFF"
        self.G.node_attr["height"] = "0.75"
        self.G.node_attr["width"] = "0.75"
        self.G.node_attr["widshapeth"] = "circle"

        self.file = file

    def flatten(self, sourcetable, fieldname, source_row_dict, target_object_row):
        source_node_name = self.generate_node_name(
            sourcetable, source_row_dict.get("name"), source_row_dict.get("id")
        )
        target_node_name = self.generate_node_name(
            target_object_row._tablename,
            getattr(target_object_row, "name"),
            target_object_row.id,
        )
        self.G.add_edge(
            source_node_name, target_node_name, fieldname, label=f"    {fieldname}     "
        )
        return target_object_row

    def generate_node_name(self, tablename, rowname, id):
        rowname = rowname or ""
        separator = ", " if rowname else ""
        return f"{tablename}({id}{separator}{rowname})"

    def write_single_row(self, tablename, row):
        node_name = self.generate_node_name(tablename, row.get("name"), row["id"])
        self.G.add_node(node_name)

    def close(self):
        self.file.write(self.G.string())


class ImageOutputStream(GraphvizOutputStream):
    def __init__(self, file, format="png"):
        self.format = format
        super().__init__(file)

    def close(self):
        self.G.draw(path=self.file, prog="dot", format=self.format)


class MultiplexOutputStream(OutputStream):
    def __init__(self, outputstreams):
        self.outputstreams = outputstreams

    def create_or_validate_tables(self, tables):
        for stream in self.outputstreams:
            stream.create_or_validate_tables(tables)

    def write_row(self, tablename, row_with_references):
        for stream in self.outputstreams:
            stream.write_row(tablename, row_with_references)

    def close(self):
        for stream in self.outputstreams:
            stream.close()

    def write_single_row(self, tablename, row):
        return super().write_single_row(tablename, row)

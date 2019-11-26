import os
from abc import abstractmethod, ABC
import json
import csv
from urllib.parse import urlparse
from pathlib import Path
from collections import namedtuple

from sqlalchemy import create_engine, MetaData, Column, Integer, Table, Unicode
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import create_session
from .data_gen_exceptions import DataGenError

from cumulusci.tasks.bulkdata.base_generate_data_task import (
    create_table as create_table_from_mapping,
)

from cumulusci.tasks.bulkdata.data_generation.data_generator_runtime import ObjectRow


class OutputStream(ABC):
    count = 1
    flush_limit = 1000
    commit_limit = 10000

    def create_or_validate_tables(self, tables):
        pass

    def flatten(self, sourcetable, fieldname, row, obj):
        return obj.id

    def flush(self):
        pass

    def commit(self):
        pass

    def write_row(self, tablename, row_with_references):
        row_with_objects_represented_by_ids = {
            fieldname: (
                self.flatten(tablename, fieldname, row_with_references, fieldvalue)
                if isinstance(fieldvalue, ObjectRow)
                else fieldvalue
            )
            for fieldname, fieldvalue in row_with_references.items()
        }
        self.write_single_row(tablename, row_with_objects_represented_by_ids)
        if self.count % self.flush_limit == 0:
            self.flush()

        if self.count % self.commit_limit == 0:
            self.commit()

        self.count += 1

    @abstractmethod
    def write_single_row(self, tablename, row):
        pass

    def close(self):
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
    def __init__(self, file):
        super().__init__()
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

    def commit(self):
        self.session.commit()

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

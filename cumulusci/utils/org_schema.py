from logging import getLogger
from pathlib import Path
from tempfile import TemporaryDirectory
import gzip
from itertools import chain
from collections import defaultdict
from typing import Optional, Dict
from email.utils import parsedate
from contextlib import ExitStack, contextmanager

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import create_session
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, attributes, ColumnProperty, exc
from cumulusci.utils.org_schema_models import Base, SObject, Field, FileMetadata
from cumulusci.utils.http.multi_request import CompositeParallelSalesforce

y2k = "Sat, 1 Jan 2000 00:00:01 GMT"


def simplify_value(name, value):
    if value == []:
        return None
    elif isinstance(value, (list, dict)):
        return value
    elif isinstance(value, (bool, int, str, type(None))):
        return value
    else:
        raise AssertionError(value)


def compute_prop_filter(model):
    return {
        name
        for name, value in vars(model).items()
        if not name.startswith("_")
        and isinstance(value, attributes.InstrumentedAttribute)
        and isinstance(value.prop, ColumnProperty)
    }


def zip_database(tempfile, schema_path):
    with tempfile.open("rb") as db, gzip.GzipFile(
        fileobj=schema_path.open("wb")
    ) as gzipped:
        gzipped.write(db.read())


def unzip_database(gzipfile, outfile):
    with gzip.GzipFile(fileobj=gzipfile.open("rb")) as gzipped, open(
        outfile, "wb"
    ) as db:
        db.write(gzipped.read())


class Schema:
    _last_modified_date = None

    def __init__(self, engine):
        self.engine = engine
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    @property
    def sobjects(self):
        return self.session.query(SObject)

    def __getitem__(self, name):
        try:
            return self.session.query(SObject).filter_by(name=name).one()
        except exc.NoResultFound:
            raise KeyError(f"No sobject named {name}")

    def __contains__(self, name):
        return self.session.query(SObject).filter_by(name=name).all()

    def keys(self):
        return (x[0] for x in self.session.query(SObject.name).all())

    def values(self):
        return self.session.query(SObject).all()

    def items(self):
        return ((obj.name, obj) for obj in self.session.query(SObject).all())

    @property
    def last_modified_date(self):
        if not self._last_modified_date:
            try:
                self._last_modified_date = (
                    self.session.query(FileMetadata)
                    .filter(FileMetadata.name == "Last-Modified")
                    .one()
                    .value
                )
            except exc.NoResultFound:
                pass
        return self._last_modified_date


class SchemaDatabasePopulater:
    def __init__(self, schema):
        self.row_buffer_count = 0
        self.session = schema.session
        self.engine = schema.engine
        self.metadata = Base.metadata

    def cache(self, sf, last_modified_date, logger=None):
        sobjs = sf.describe()["sobjects"]
        sobj_names = [obj["name"] for obj in sobjs]

        full_sobjs = deep_describe(sf, last_modified_date, sobj_names)

        Base.metadata.bind = self.engine
        self.metadata.reflect()

        self.buffered_session = BufferedSession(self.engine, Base.metadata)

        max_last_modified = (parsedate(last_modified_date), last_modified_date)
        for (sobj_data, last_modified) in full_sobjs:
            fields = sobj_data.pop("fields")
            self.create_row(SObject, sobj_data)
            for field in fields:
                field["sobject"] = sobj_data["name"]
                self.create_row(Field, field)
                sortable = parsedate(last_modified), last_modified
                if sortable > max_last_modified:
                    max_last_modified = sortable

        self.create_row(
            FileMetadata, {"name": "Last-Modified", "value": max_last_modified[1]}
        )
        self.create_row(FileMetadata, {"name": "FormatVersion", "value": 1})
        self.buffered_session.commit()
        self.engine.execute("vacuum")
        return

    def create_row(self, model, valuesdict):
        values = {
            name: simplify_value(name, value) for name, value in valuesdict.items()
        }
        self.buffered_session.write_single_row(model.__tablename__, values)

    def create_rows(self, model, dicts):
        for dict in dicts:
            self.create_row(model, dict)
        self.buffered_session.commit()


class BufferedSession:
    def __init__(self, engine: Engine, metadata: MetaData, max_buffer_size: int = 1000):
        self.buffered_rows = defaultdict(list)
        self.engine = engine
        self.session = create_session(bind=self.engine, autocommit=False)
        self.metadata = metadata
        self._prepare()
        self.max_buffer_size = max_buffer_size

    def _prepare(self):
        # Setup table info used by the write-buffering infrastructure
        assert self.metadata.tables
        self.insert_statements = {}
        for tablename, model in self.metadata.tables.items():
            self.insert_statements[tablename] = model.insert(
                bind=self.engine, inline=True
            )

    @classmethod
    def from_url(cls, db_url: str, mappings: Optional[Dict] = None):
        engine = create_engine(db_url)
        self = cls(engine, mappings)
        return self

    def write_single_row(self, tablename: str, row: Dict) -> None:
        # cache the value for later insert
        self.buffered_rows[tablename].append(row)
        if len(self.buffered_rows[tablename]) > self.max_buffer_size:
            self.flush()

    def flush(self):
        for tablename, insert_statement in self.insert_statements.items():

            # Make sure every row has the same records per SQLAlchemy's rules

            # According to the SQL Alchemy docs, every dictionary in a set must
            # have the same keys.

            # This means that the INSERT statement will be more bloated but it
            # seems much more efficient than line-by-line inserts.
            if self.buffered_rows[tablename]:
                self.session.execute(insert_statement, self.buffered_rows[tablename])
                self.buffered_rows[tablename] = []
        self.session.flush()

    def commit(self):
        self.flush()
        self.session.commit()

    def close(self) -> None:
        self.commit()
        self.session.close()


@contextmanager
def get_org_schema(sf, org_config, force_recache=False, logger=None):
    """
    TODO: docs
    Recache: True - replace cache. False - raise if cache was not used. Default: use cache if available
    """
    assert org_config.get_orginfo_cache_dir

    with org_config.get_orginfo_cache_dir(Schema.__module__) as directory:
        directory.mkdir(exist_ok=True, parents=True)
        schema_path = directory / "org_schema.db.gz"

        if force_recache and schema_path.exists():
            schema_path.unlink()

        logger = logger or getLogger("get_org_schema")

        with ExitStack() as e:
            tempdir = TemporaryDirectory()
            e.enter_context(tempdir)
            tempfile = Path(tempdir.name) / "temp_org_schema.db"
            schema = None
            if schema_path.exists():
                unzip_database(schema_path, tempfile)
                try:
                    engine = create_engine(f"sqlite:///{str(tempfile)}")

                    schema = Schema(engine)
                    schema.from_cache = True
                except Exception as e:
                    logger.warning(
                        f"Cannot read `{schema_path}` due to {e}: recreating`"
                    )
                    schema_path.unlink()

            if not schema:
                engine = create_engine(f"sqlite:///{str(tempfile)}")
                Base.metadata.bind = engine
                Base.metadata.create_all()
                schema = Schema(engine)
                schema.from_cache = False

            SchemaDatabasePopulater(schema).cache(
                sf, schema.last_modified_date or y2k, logger,
            )
            # save a gzipped copy for later
            zip_database(tempfile, schema_path)
            yield schema


def _cache_org_schema(schema_path: Path, sf, logger):
    if schema_path.suffix != ".gz":
        schema = Schema(schema_path)
        schema._fill_cache(sf, logger)
        return schema
    else:
        with TemporaryDirectory() as tempdir:
            tempfile = Path(tempdir) / "temp_org_schema.db"
            with Schema(tempfile) as schema:
                schema._fill_cache(sf, logger)

            with tempfile.open("rb") as db, gzip.GzipFile(
                fileobj=schema_path.open("wb")
            ) as gzipped:
                gzipped.write(db.read())
            return Schema(schema_path)


def deep_describe(sf, last_modified_date, objs):
    last_modified_date = last_modified_date or y2k
    with CompositeParallelSalesforce(sf, max_workers=8) as cpsf:
        results = cpsf.composite_requests(
            (
                {
                    "method": "GET",
                    "url": f"/services/data/v48.0/sobjects/{obj}/describe",
                    "referenceId": f"ref{obj}",
                    "httpHeaders": {"If-Modified-Since": last_modified_date},
                }
                for obj in objs
            )
        )

        def validate(x):
            if isinstance(x, list):
                assert "errorCode" not in x[0], x
                print(x)
            return x

        sobjects = chain.from_iterable(
            validate(result.json())["compositeResponse"] for result in results
        )
        changes = (
            (record["body"], record["httpHeaders"]["Last-Modified"])
            for record in sobjects
            if record["httpStatusCode"] == 200
        )
        yield from changes


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    def test(schema):
        print(schema["Account"].fields["Id"].label)
        print(list(schema.keys())[0:10])
        print(list(schema.values())[0:10])
        assert "npsp__Foo__c" not in schema
        assert "Contact" in schema
        print(schema.sobjects.filter(SObject.name.like(r"%\_\_c")).all())

    def init_cci():
        from cumulusci.cli.runtime import CliRuntime

        from cumulusci.salesforce_api.utils import get_simple_salesforce_connection

        runtime = CliRuntime(load_keychain=True)
        name, org_config = runtime.get_org("qa")
        sf = get_simple_salesforce_connection(runtime.project_config, org_config)
        return sf, org_config, runtime

    sf, org_config, runtime = init_cci()

    with get_org_schema(sf, org_config, force_recache=True) as schema:
        print(schema.from_cache)
        test(schema)

    with get_org_schema(sf, org_config) as schema:
        print(schema.from_cache)
        test(schema)

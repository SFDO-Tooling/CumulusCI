from logging import getLogger
from pathlib import Path
from tempfile import TemporaryDirectory
import gzip
from itertools import chain
from collections import defaultdict
from typing import Optional, Dict

from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import create_session
from sqlalchemy.engine import Engine
from sqlalchemy.sql import select
from sqlalchemy.orm import sessionmaker, attributes, ColumnProperty, exc
from cumulusci.utils.org_schema.models import Base, SObject, Field, FileMetadata
from cumulusci.utils.http.multi_request import CompositeParallelSalesforce


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


def _org_max_revision(sf):
    qr = sf.restful("tooling/query", {"q": "select Max(RevisionNum) from SourceMember"})
    res = qr["records"][0]["expr0"]
    if res:
        return int(res)
    else:
        raise AssertionError()  # TODO


class Schema:
    engine = None
    tempdir = None

    def __init__(self, path):
        if path.suffix == ".gz":
            self.tempdir = TemporaryDirectory()
            self.tempfile = Path(self.tempdir.name) / "temp_org_schema.db"
            with gzip.open(path, "rb") as gzipped, open(self.tempfile, "wb") as db:
                db.write(gzipped.read())
            path = str(self.tempfile)
        self.engine = create_engine(f"sqlite:///{path}")

        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    @property
    def sobjects(self):
        return self.session.query(SObject)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        self.session.close()
        if self.tempdir:
            self.tempdir.cleanup()
            self.tempdir = None
        self.session = "CLOSED"
        self.engine = "CLOSED"

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
    def schema_revision(self):
        return self.session.query(FileMetadata).one().schema_revision

    def _fill_cache(self, sf, logger=None):
        SchemaCacher(self).cache(sf, logger)


class SchemaCacher:
    def __init__(self, schema):
        self.row_buffer_size = 500
        self.row_buffer_count = 0
        self.session = schema.session
        self.engine = schema.engine
        self.metadata = Base.metadata

    def cache(self, sf, logger=None):
        sobjs = sf.describe()["sobjects"]
        sobj_names = [obj["name"] for obj in sobjs]
        full_sobjs = deep_describe(sf, objs=sobj_names)

        Base.metadata.bind = self.engine
        Base.metadata.create_all()

        self.buffered_session = BufferedSession(self.engine, Base.metadata)

        self.create_rows(
            SObject, sobjs,
        )

        # sobj_rows = self.session.query(SObject).options(load_only("id", "name"))
        select_sobj_rows = select([SObject.__table__.c.id, SObject.__table__.c.name])
        result = self.engine.execute(select_sobj_rows)
        sobj_ids = {obj.name: obj.id for obj in result}

        for sobj_data in full_sobjs:
            for field in sobj_data["fields"]:
                field["parent_id"] = sobj_ids[sobj_data["name"]]
                self.create_row(Field, field)
        self.buffered_session.commit()

        # create_row(session, FileMetadata, {"schema_revision": current_revision})
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
    def __init__(self, engine: Engine, metadata: MetaData):
        self.buffered_rows = defaultdict(list)
        self.engine = engine
        self.session = create_session(bind=self.engine, autocommit=False)
        self.metadata = metadata
        self._prepare()

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
        if len(self.buffered_rows[tablename]) > 1000:
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


def get_org_schema(sf, project_config, org_config, logger=None, recache: bool = None):
    """
    TODO: docs
    Recache: True - replace cache. False - raise if cache was not used. Default: use cache if available
    """
    directory = project_config.project_cache_dir / "orgs" / sf.sf_instance
    directory.mkdir(exist_ok=True, parents=True)
    schema_path = directory / "org_schema.db.gz"
    logger = logger or getLogger("get_org_schema")

    if schema_path.exists() and not recache:
        try:
            old_schema = find_old_schema(schema_path)
            if old_schema:
                return old_schema
        except Exception as e:
            if recache is False:
                raise
            logger.warning(f"Cannot read `{schema_path}` due to {e}: recreating`")

    if Path(schema_path).exists():
        Path(schema_path).unlink()
    try:
        return _cache_org_schema(schema_path, sf, logger)
    except Exception:
        if Path(schema_path).exists():
            Path(schema_path).unlink()
        raise

    schema = Schema(schema_path)
    schema.from_cache = False
    return schema


def find_old_schema(schema_path):
    return None
    old_schema = Schema(schema_path)

    if old_schema:
        current_revision = int(_org_max_revision(sf))
        if old_schema.schema_revision == current_revision and old_schema.file:
            old_schema.from_cache = True
            return old_schema


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

            with open(tempfile, "rb") as db, gzip.open(schema_path, "wb") as gzipped:
                gzipped.write(db.read())
            return Schema(schema_path)


def deep_describe(sf, last_modified_date="Fri, 1 Aug 2000 01:01:01 GMT", objs=()):
    objs = objs or [obj["name"] for obj in sf.describe()["sobjects"]]
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
        sobjects = chain.from_iterable(
            result.json()["compositeResponse"] for result in results
        )
        changes = (
            record["body"] for record in sobjects if record["httpStatusCode"] == 200
        )
        yield from changes


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    def test(schema):
        print(schema["Account"].fields["Id"].label)
        print(list(schema.keys())[0:10])
        print(list(schema.values())[0:10])
        print("npsp__Foo__c" in schema)
        print("Contact" in schema)
        print(schema.sobjects.filter(SObject.name.like(r"%\_\_c")).all())

    def init_cci():
        from cumulusci.cli.runtime import CliRuntime

        from cumulusci.salesforce_api.utils import get_simple_salesforce_connection

        runtime = CliRuntime(load_keychain=True)
        name, org_config = runtime.get_org("qa")
        sf = get_simple_salesforce_connection(runtime.project_config, org_config)
        return sf, runtime

    sf, runtime = init_cci()

    schema = get_org_schema(sf, runtime.project_config, recache=True)
    with schema:
        test(schema)

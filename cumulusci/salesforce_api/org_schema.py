import gzip
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from email.utils import parsedate
from logging import getLogger
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import create_session, exc, sessionmaker

from cumulusci.salesforce_api.org_schema_models import (
    Base,
    Field,
    FileMetadata,
    SObject,
)
from cumulusci.utils.http.multi_request import CompositeParallelSalesforce

y2k = "Sat, 1 Jan 2000 00:00:01 GMT"


def zip_database(tempfile, schema_path):
    """Compress tempfile.db to schema_path.db.gz"""
    with tempfile.open("rb") as db:
        with schema_path.open("wb") as fileobj:
            with gzip.GzipFile(fileobj=fileobj, mode="w") as gzipped:
                gzipped.write(db.read())


def unzip_database(gzipfile, outfile):
    """Decompress schema_path.db.gz to outfile.db"""
    with gzipfile.open("rb") as fileobj:
        with gzip.GzipFile(fileobj=fileobj) as gzipped:
            with open(outfile, "wb") as db:
                db.write(gzipped.read())


class Schema:
    """Represents an org's schema, cached from describe() calls"""

    _last_modified_date = None

    def __init__(self, engine, schema_path):
        self.engine = engine
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.path = schema_path

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

    def block_writing(self):
        """After this method is called, the database can't be updated again"""
        # changes don't get saved back to the gzip
        # so there is no point writing to the DB
        def closed():
            raise IOError("Database is not open for writing")

        self.session._real_commit__ = self.session.commit
        self.session.commit = closed

    def close(self):
        self.session.close()

    @property
    def last_modified_date(self):
        """Date of the most recent schema update"""
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

    def __repr__(self):
        return f"<Schema {self.path} : {self.engine}>"

    def populate_cache(self, sf, last_modified_date, logger=None):
        """Populate a schema cache from the API, using last_modified_date
        to pull down only new schema"""

        sobjs = sf.describe()["sobjects"]
        sobj_names = [obj["name"] for obj in sobjs]

        responses = list(deep_describe(sf, last_modified_date, sobj_names))
        changes = [
            (resp.body, resp.last_modified_date)
            for resp in responses
            if resp.status == 200
        ]
        unexpected = [resp for resp in responses if resp.status not in (200, 304)]
        for unknown in unexpected:
            logger.warning(
                f"Unexpected describe reply. An SObject may be missing: {unknown}"
            )
        self._populate_cache_from_describe(changes, last_modified_date)

    def _populate_cache_from_describe(
        self, describe_objs: List[Tuple[dict, str]], last_modified_date
    ):
        """Populate a schema cache from a list of describe objects."""
        engine = self.engine
        metadata = Base.metadata
        metadata.bind = engine
        metadata.reflect()

        with BufferedSession(engine, metadata) as sess:

            max_last_modified = (parsedate(last_modified_date), last_modified_date)
            for (sobj_data, last_modified) in describe_objs:
                fields = sobj_data.pop("fields")
                create_row(sess, SObject, sobj_data)
                for field in fields:
                    field["sobject"] = sobj_data["name"]
                    create_row(sess, Field, field)
                    sortable = parsedate(last_modified), last_modified
                    if sortable > max_last_modified:
                        max_last_modified = sortable

            create_row(
                sess,
                FileMetadata,
                {"name": "Last-Modified", "value": max_last_modified[1]},
            )
            create_row(sess, FileMetadata, {"name": "FormatVersion", "value": 1})

        engine.execute("vacuum")


def create_row(buffered_session: "BufferedSession", model, valuesdict: dict):
    buffered_session.write_single_row(model.__tablename__, valuesdict)


class BufferedSession:
    """Buffer writes to a SQL DB for faster performmance"""

    def __init__(self, engine: Engine, metadata: MetaData, max_buffer_size: int = 1000):
        self.buffered_rows = defaultdict(list)
        self.columns = {}
        self.engine = engine
        self.metadata = metadata
        self._prepare()
        self.max_buffer_size = max_buffer_size

    def __enter__(self, *args):
        self.session = create_session(bind=self.engine, autocommit=False)
        return self

    def __exit__(self, *args):
        self.close()

    def _prepare(self):
        # Setup table info used by the write-buffering infrastructure
        assert self.metadata.tables
        self.insert_statements = {}
        for tablename, model in self.metadata.tables.items():
            self.insert_statements[tablename] = model.insert(bind=self.engine)
            self.columns[tablename] = {
                colname: None for colname in model.columns.keys()
            }

    def write_single_row(self, tablename: str, row: Dict) -> None:
        # but first, normalize it so all keys have a value. SQLite Requires it.
        normalized_row = {}
        for key, default in self.columns[tablename].items():
            normalized_row[key] = row.get(key, default)

        # cache the value for later insert
        self.buffered_rows[tablename].append(normalized_row)

        # flush if buffer is full
        if len(self.buffered_rows[tablename]) > self.max_buffer_size:
            self.flush()

    def flush(self):
        for tablename, insert_statement in self.insert_statements.items():
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
    Get a read-only representation of an org's schema.

    org_config - an OrgConfig for the relevant org
    force_recache: True - replace cache. False (default) - use/update cache is available.
    logger - replace the standard logger "cumulusci.salesforce_api.org_schema"
    """
    with org_config.get_orginfo_cache_dir(Schema.__module__) as directory:
        directory.mkdir(exist_ok=True, parents=True)
        schema_path = directory / "org_schema.db.gz"

        if force_recache and schema_path.exists():
            schema_path.unlink()

        logger = logger or getLogger(__name__)

        with ExitStack() as closer:
            tempdir = TemporaryDirectory()
            closer.enter_context(tempdir)
            tempfile = Path(tempdir.name) / "temp_org_schema.db"
            schema = None
            if schema_path.exists():
                try:
                    cleanups_on_failure = []
                    unzip_database(schema_path, tempfile)
                    cleanups_on_failure.extend([schema_path.unlink, tempfile.unlink])
                    engine = create_engine(f"sqlite:///{str(tempfile)}")

                    schema = Schema(engine, schema_path)
                    cleanups_on_failure.append(schema.close)
                    closer.callback(schema.close)
                    assert schema.sobjects.first().name
                    schema.from_cache = True
                except Exception as e:
                    logger.warning(
                        f"Cannot read `{schema_path}`. Recreating it. Reason `{e}`."
                    )
                    schema = None
                    for cleanup_action in reversed(cleanups_on_failure):
                        cleanup_action()

            if schema is None:
                engine = create_engine(f"sqlite:///{str(tempfile)}")
                Base.metadata.bind = engine
                Base.metadata.create_all()
                schema = Schema(engine, schema_path)
                closer.callback(schema.close)
                schema.from_cache = False

            schema.populate_cache(
                sf,
                schema.last_modified_date or y2k,
                logger,
            )
            schema.block_writing()
            # save a gzipped copy for later
            zip_database(tempfile, schema_path)
            yield schema


class DescribeResponse(NamedTuple):
    """Result of a describe call from Salesforce"""

    status: int
    body: dict
    last_modified_date: str = None
    refId: str = None


def deep_describe(
    sf, last_modified_date: Optional[str], objs: List[str]
) -> Iterable[DescribeResponse]:
    """Fetch describe data for changed sobjects

    Fetch describe data for sobjects from the list 'objs'
    which have changed since last_modified_date (in HTTP
    proto format) and yield each object as a DescribeResponse object."""
    last_modified_date = last_modified_date or y2k
    with CompositeParallelSalesforce(sf, max_workers=8) as cpsf:
        responses = cpsf.do_composite_requests(
            (
                {
                    "method": "GET",
                    "url": f"/services/data/v{sf.sf_version}/sobjects/{obj}/describe",
                    "referenceId": f"ref{obj}",
                    "httpHeaders": {"If-Modified-Since": last_modified_date},
                }
                for obj in objs
            )
        )

        responses = (
            DescribeResponse(
                response["httpStatusCode"],
                response["body"],
                response["httpHeaders"].get("Last-Modified"),
                response["referenceId"],
            )
            for response in responses
        )
        yield from responses

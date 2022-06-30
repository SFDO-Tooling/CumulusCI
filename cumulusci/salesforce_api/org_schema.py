import gzip
import re
import typing as T
from collections import defaultdict
from contextlib import ExitStack, contextmanager
from email.utils import parsedate
from enum import Enum
from logging import getLogger
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Iterable, List, NamedTuple, Optional, Tuple

from sqlalchemy import MetaData, create_engine, not_
from sqlalchemy.engine import Engine
from sqlalchemy.orm import create_session, exc, sessionmaker

from cumulusci.salesforce_api.org_schema_models import (
    Base,
    Field,
    FileMetadata,
    SObject,
)
from cumulusci.utils.http.multi_request import (
    RECOVERABLE_ERRORS,
    CompositeParallelSalesforce,
)
from cumulusci.utils.salesforce.count_sobjects import count_sobjects

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


def ignore_based_on_name(objname, patterns: T.Sequence[re.Pattern]):
    return any(pat.fullmatch(objname) for pat in patterns)


class Filters(Enum):
    """Options for filtering schemas"""

    # These were originally done using SQL Alchemy syntax because filtering
    # was done in SQL Alchemy. It is still possible to use them that way
    # in client code:
    #
    # schema.objects.filter(Filters.activateable)
    activateable = SObject.activateable
    compactLayoutable = SObject.compactLayoutable
    createable = SObject.createable
    deepCloneable = SObject.deepCloneable
    deletable = SObject.deletable
    layoutable = SObject.layoutable
    listviewable = SObject.listviewable
    lookupLayoutable = SObject.lookupLayoutable
    mergeable = SObject.mergeable
    queryable = SObject.queryable
    replicateable = SObject.replicateable
    retrieveable = SObject.retrieveable
    searchLayoutable = SObject.searchLayoutable
    searchable = SObject.searchable
    triggerable = SObject.triggerable
    undeletable = SObject.undeletable
    updateable = SObject.updateable

    not_activateable = not_(SObject.activateable)
    not_compactLayoutable = not_(SObject.compactLayoutable)
    not_createable = not_(SObject.createable)
    not_deepCloneable = not_(SObject.deepCloneable)
    not_deletable = not_(SObject.deletable)
    not_layoutable = not_(SObject.layoutable)
    not_listviewable = not_(SObject.listviewable)
    not_lookupLayoutable = not_(SObject.lookupLayoutable)
    not_mergeable = not_(SObject.mergeable)
    not_queryable = not_(SObject.queryable)
    not_replicateable = not_(SObject.replicateable)
    not_retrieveable = not_(SObject.retrieveable)
    not_searchLayoutable = not_(SObject.searchLayoutable)
    not_searchable = not_(SObject.searchable)
    not_triggerable = not_(SObject.triggerable)
    not_undeletable = not_(SObject.undeletable)
    not_updateable = not_(SObject.updateable)

    extractable = "extractable"  # can it be extracted safely?
    # non-extractable objects are discovered
    # through experimentation.
    # Also, all non-queryable and non-retrievable objects are
    # considered non-extractable.

    populated = SObject.count > 0  # does it have data in the org?


class Schema:
    """Represents an org's schema, cached from describe() calls"""

    _last_modified_date = None
    included_objects = None

    def __init__(self, engine, schema_path):
        self.engine = engine
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.path = schema_path

    @property
    def sobjects(self):
        query = self.session.query(SObject)
        if self.included_objects:
            query = query.filter(SObject.name.in_(self.included_objects))
        return query

    def __getitem__(self, name):
        try:
            return self.sobjects.filter_by(name=name).one()
        except exc.NoResultFound:
            raise KeyError(f"No sobject named {name}")

    def __contains__(self, name):
        return self.sobjects.filter_by(name=name).all()

    def keys(self):
        return [x.name for x in self.sobjects.all()]

    def values(self):
        return self.sobjects.all()

    def items(self):
        return [(obj.name, obj) for obj in self.sobjects]

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

    def populate_cache(
        self,
        sf,
        included_objects,
        last_modified_date,
        filters: T.Sequence[Filters] = (),
        patterns_to_ignore: T.Sequence[str] = (),
        logger=None,
    ) -> T.List[str]:
        """Populate a schema cache from the API, using last_modified_date
        to pull down only new schema"""
        for pat in patterns_to_ignore:
            assert pat.replace("%", "").isalpha(), f"Pattern has wrong chars {pat}"

        # Platform bug!
        patterns_to_ignore = ("MacroInstruction%",) + tuple(patterns_to_ignore)
        regexps_to_ignore = [
            re.compile(pat.replace("%", ".*"), re.IGNORECASE)
            for pat in patterns_to_ignore
        ]

        objs = [obj for obj in sf.describe()["sobjects"]]
        if included_objects:
            objs = [obj for obj in objs if obj["name"] in included_objects]
        sobj_names = [
            obj["name"]
            for obj in objs
            if not (
                ignore_based_on_name(obj["name"], regexps_to_ignore)
                or ignore_based_on_properties(obj, filters)
            )
        ]

        responses = list(deep_describe(sf, last_modified_date, sobj_names, logger))
        changes = [
            (resp.body, resp.last_modified_date)
            for resp in responses
            if resp.status == 200
        ]
        unexpected = [resp for resp in responses if resp.status not in (200, 304)]
        for unknown in unexpected:  # pragma: no cover
            logger.warning(
                f"Unexpected describe reply. An SObject may be missing: {unknown}"
            )
        self._populate_cache_from_describe(changes, last_modified_date)
        return sobj_names

    def _populate_cache_from_describe(
        self, describe_objs: List[Tuple[dict, str]], last_modified_date
    ) -> T.List[str]:
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
def get_org_schema(
    sf,
    org_config,
    *,
    include_counts: bool = False,
    filters: T.Sequence[Filters] = (),
    patterns_to_ignore: T.Tuple[str] = (),
    included_objects: T.List[str] = (),
    force_recache=False,
    logger=None,
):
    """
    Get a read-only representation of an org's schema.
    sf - simple_saleforce object
    org_config - an OrgConfig for the relevant org

    include_counts: query each queryable/retrievable object count.
                    This takes time and may even timeout in huge orgs!
    filters: A sequence of Filters which are the same as Salesforce SObject properties
            like .createable, .deletable etc. Objects that do not match are ignored.
            Two special filters exist:
                * Filters.extractable, which uses heuristics to limit to objects
                    that extract properly
                * Filters.populated, which limits to objects that have data in them.
                    This depends upon `include_counts`
    included_objects: Ignore objects not in this list. Stacks with other filters
    patterns_to_ignore: Strings in SQL %LIKE% syntax that match SObjects to be
                        ignored.

    force_recache: True - replace cache. False (default) - use/update cache is available.
    logger - replace the standard logger "cumulusci.salesforce_api.org_schema"
    """
    assert not isinstance(patterns_to_ignore, str)

    filters = set(filters)
    with org_config.get_orginfo_cache_dir(Schema.__module__) as directory:
        directory.mkdir(exist_ok=True, parents=True)
        schema_path = directory / "org_schema.db.gz"

        if force_recache and schema_path.exists():
            schema_path.unlink()

        if Filters.populated in filters:
            filters.add(Filters.queryable)
            filters.add(Filters.retrieveable)
            # experiment with removing this limitation by using limit 1 query instead
            assert include_counts, "Filters.populated depends on include_counts"
            patterns_to_ignore += NOT_COUNTABLE

        if Filters.extractable in filters:
            filters.add(Filters.queryable)
            filters.add(Filters.retrieveable)
            patterns_to_ignore += NOT_EXTRACTABLE

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
                    schema = Schema(
                        engine,
                        schema_path,
                    )

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
                schema = Schema(
                    engine,
                    schema_path,
                )
                closer.callback(schema.close)
                schema.from_cache = False

            objs_cached = schema.populate_cache(
                sf,
                included_objects,
                schema.last_modified_date or y2k,
                filters,
                patterns_to_ignore,
                logger,
            )
            if include_counts:
                objs_counted = populate_counts(sf, schema, objs_cached, logger)

            if Filters.populated in filters:
                # another way to compute this might be by querying the first ID
                objs_cached = [objname for objname, count in objs_counted if count > 0]
            schema.included_objects = objs_cached
            schema.block_writing()
            # save a gzipped copy for later
            zip_database(tempfile, schema_path)
            yield schema


def populate_counts(sf, schema, objs_cached, logger):
    objects_to_count = [objname for objname in objs_cached]
    counts, transports_errors, salesforce_errors = count_sobjects(sf, objects_to_count)
    errors = transports_errors + salesforce_errors
    for error in errors[0:10]:
        logger.warning(f"Error counting SObjects: {error}")

    if len(errors) > 10:
        logger.warning(f"{len(errors)} more counting errors surpressed")

    for objname, count in counts.items():
        schema[objname].count = count
    schema.session.flush()
    return counts.items()


class DescribeResponse(NamedTuple):
    """Result of a describe call from Salesforce"""

    status: int
    body: dict
    last_modified_date: str = None


def deep_describe(
    sf, last_modified_date: Optional[str], objs: List[str], logger
) -> Iterable[DescribeResponse]:
    """Fetch describe data for changed sobjects

    Fetch describe data for sobjects from the list 'objs'
    which have changed since last_modified_date (in HTTP
    proto format) and yield each object as a DescribeResponse object."""

    logger = logger or getLogger(__name__)
    last_modified_date = last_modified_date or y2k
    with CompositeParallelSalesforce(sf, max_workers=8) as cpsf:
        responses, errors = cpsf.do_composite_requests(
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

        for error in errors[0:5]:
            logger.warning(f"Error calling Salesforce API: {error}")
        if len(errors) > 5:
            logger.warning(f"...Total {len(errors)} errors")

        unrecoverable_errors = (
            error
            for error, matching_request in errors
            if not isinstance(error, RECOVERABLE_ERRORS)
        )
        first_unrecoverable_error = next(unrecoverable_errors, None)
        if first_unrecoverable_error:
            raise first_unrecoverable_error

        responses = (
            DescribeResponse(
                response["httpStatusCode"],
                response["body"],
                response["httpHeaders"].get("Last-Modified"),
            )
            for response in responses
        )
        yield from responses


def ignore_based_on_properties(obj: dict, filters: T.Sequence[Filters]):
    if all(obj.get(filter.name, True) for filter in filters):
        return False
    else:
        return True


NOT_COUNTABLE = (
    "ContentDocumentLink",  # ContentDocumentLink requires a filter by a single Id on ContentDocumentId or LinkedEntityId
    "ContentFolder%",  # Implementation restriction: ContentFolderItem requires a filter by Id or ParentContentFolderId
    "IdeaComment",  # you must filter using the following syntax: CommunityId = [single ID],
    "Vote",  # you must filter using the following syntax: ParentId = [single ID],
    "RecordActionHistory",  # Gack: 1133111327-118855 (1126216936)
)


NOT_EXTRACTABLE = NOT_COUNTABLE + (
    "%permission%",
    "%use%",
    "%access%",
    "group",
    "%share",
    "NetworkUserHistoryRecent",
    "OutgoingEmail",
    "OutgoingEmailRelation",
)

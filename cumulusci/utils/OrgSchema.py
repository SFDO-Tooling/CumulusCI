from time import time
from logging import getLogger
from pathlib import Path
from tempfile import TemporaryDirectory
import gzip

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, attributes, ColumnProperty, exc
from cumulusci.utils.org_schema.models import Base, SObject, Field, FileMetadata


def simplify_value(name, value):
    if value == []:
        return None
    elif isinstance(value, (list, dict)):
        return value
    elif isinstance(value, (bool, int, str, type(None))):
        return value
    else:
        raise AssertionError(value)


def create_row(session, model, valuesdict):
    values = {name: simplify_value(name, value) for name, value in valuesdict.items()}

    row = model(**values)
    session.add(row)
    session.commit()


def compute_prop_filter(model):
    return {
        name
        for name, value in vars(model).items()
        if not name.startswith("_")
        and isinstance(value, attributes.InstrumentedAttribute)
        and isinstance(value.prop, ColumnProperty)
    }


def create_rows(session, model, dicts):
    for dict in dicts:
        create_row(session, model, dict)


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
            raise KeyError(f"No sobject named f{name}")

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
        all_sobjs = sf.describe()["sobjects"]
        session = self.session

        Base.metadata.create_all(self.engine)

        progress = progress_logger(len(all_sobjs) + 1, 10, logger)

        create_rows(
            session, SObject, all_sobjs,
        )
        next(progress)

        current_revision = int(_org_max_revision(sf))
        # picklist_filters = compute_prop_filter(PickListValue)

        for sobj in all_sobjs:
            sobj_data = getattr(sf, sobj["name"]).describe()
            for field in sobj_data["fields"]:
                field["parent_id"] = (
                    session.query(SObject).filter(SObject.name == sobj["name"]).one().id
                )
                create_row(session, Field, field)
            next(progress)

        create_row(session, FileMetadata, {"schema_revision": current_revision})
        self.engine.execute("vacuum")
        return


def get_org_schema(sf, project_config, logger=None, recache: bool = None):
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


def progress_logger(target_count, report_when, logger):
    if not logger:
        return
    last_report = time()
    counter = 0
    while True:
        yield counter
        counter += 1
        if time() - last_report > report_when:
            last_report = time()
            logger.info(f"Completed {counter}/{target_count}")


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

from DataGenerator import Context

from sqlalchemy import MetaData, create_engine
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import create_session

from cumulusci.tasks.bulkdata.utils import create_table


class OutputStream:
    def output_batches(self, factories, number, variables):
        context = Context(None, None, self, variables)
        for i in range(0, number):
            for factory in factories:
                self.output(factory, context)

    def output(self, factory, context):
        return factory.generate_rows(self, context)

    def write_row(self, tablename, row):
        assert 0, "Not implemented"


class DebugOutputEngine(OutputStream):
    def write_row(self, tablename, row):
        print(tablename, row)


class SqlOutputEngine(OutputStream):
    def init_db(self, db_url, mappings):
        engine = create_engine(db_url)
        metadata = MetaData()
        metadata.bind = engine
        for mapping in mappings.values():
            create_table(mapping, metadata)
        metadata.create_all()
        base = automap_base(bind=engine, metadata=metadata)
        base.prepare(engine, reflect=True)
        session = create_session(bind=engine, autocommit=False)
        return session, engine, base
